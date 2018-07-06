#!/usr/bin/env python3
"""Model module."""
from datetime import datetime
from urllib.parse import urlparse
import json
import os

from flask import flash
from flask_admin.babel import gettext
from flask_sqlalchemy import SQLAlchemy
from requests_html import HTMLSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import attributes as orm_attributes, relationship
from sqlalchemy.types import TIMESTAMP
from sqlalchemy_utils.types import ChoiceType, JSONType, ScalarListType, URLType
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
import requests
import structlog

from . import plugin


log = structlog.getLogger(__name__)
db = SQLAlchemy()

url_tags = db.Table(
    'url_tags',
    db.Column('url_id', db.Integer, db.ForeignKey('url.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))
match_result_tags = db.Table(
    'match_result_tags',
    db.Column('match_result_idd', db.Integer, db.ForeignKey('match_result.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))
search_image_match_results = db.Table(
    'search_image_match_results',
    db.Column('search_image_page_id', db.Integer, db.ForeignKey('search_image_page.id'), primary_key=True),   # NOQA
    db.Column('match_result_id', db.Integer, db.ForeignKey('match_result.id'), primary_key=True))
search_query_match_results = db.Table(
    'search_query_match_results',
    db.Column('search_query_id', db.Integer, db.ForeignKey('search_query.id'), primary_key=True),
    db.Column('match_result_id', db.Integer, db.ForeignKey('match_result.id'), primary_key=True))


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(TIMESTAMP, default=datetime.now, nullable=False)


class SingleStringModel(Base):
    __abstract__ = True
    value = db.Column(db.String)


class Url(Base):
    value = db.Column(URLType, unique=True, nullable=False)
    tags = db.relationship(
        'Tag', secondary=url_tags, lazy='subquery',
        backref=db.backref('urls', lazy=True))

    @hybrid_property
    def filename(self):
        url = str(self.value)
        return os.path.splitext(os.path.basename(url))[0]

    @hybrid_property
    def content_type(self):
        res = []
        if not isinstance(self.responses, orm_attributes.InstrumentedAttribute):
            res.extend(set(sum([x.content_type for x in self.responses], [])))
        if not isinstance(self.on_final_responses, orm_attributes.InstrumentedAttribute):
            res.extend(set(sum([x.content_type for x in self.on_final_responses], [])))
        return set(res)

    def __repr__(self):
        templ = '<Url:{0.id} {0.value}>'
        return templ.format(self)


class SearchQuery(Base):
    """Search query."""
    search_term = db.Column(db.String, nullable=False)
    page = db.Column(db.Integer, nullable=False, default=1)
    match_results = db.relationship(
        'MatchResult', secondary=search_query_match_results, lazy='subquery',
        backref=db.backref('search_queries', lazy=True))
    mode_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    mode = db.relationship(
        'Plugin', foreign_keys='SearchQuery.mode_id', lazy='subquery',
        backref=db.backref('search_queries', lazy=True, cascade='delete'))

    def __repr__(self):
        templ = \
            '<SearchQuery:{0.id} q:[{0.search_term}] p:{0.page} mode:{1}>'
        return templ.format(self, self.mode.name if self.mode else '')

    @classmethod
    def create(
            cls, form, session,
            on_model_change_func=None, handle_view_exception=None, after_model_change_func=None
    ):
        try:
            model = get_or_create(
                session, SearchQuery,
                search_term=form.search_term.data, page=form.page.data, mode=form.mode.data
            )[0]
            pm = get_plugin_manager()
            plugin = pm.getPluginByName(model.mode.name, model.mode.category)
            mrs = list(set(plugin.plugin_object.get_match_results(
                search_term=model.search_term, page=model.page, session=session)))
            model.match_results.extend(mrs)
            session.add(model)
            if on_model_change_func:
                on_model_change_func(form, model, True)
            session.commit()
        except Exception as ex:
            if handle_view_exception and handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                log.exception('Failed to create record.')
            session.rollback()
            return False
        else:
            if after_model_change_func:
                after_model_change_func(form, model, True)
        return model


class MatchResult(Base):
    """Match result."""
    url_id = db.Column(db.Integer, db.ForeignKey('url.id'))
    url = db.relationship(
        'Url', foreign_keys='MatchResult.url_id', lazy='subquery',
        backref=db.backref('match_results', lazy=True, cascade='delete'))
    thumbnail_url_id = db.Column(db.Integer, db.ForeignKey('url.id'))
    thumbnail_url = relationship(
        'Url', foreign_keys='MatchResult.thumbnail_url_id', lazy='subquery',
        backref=db.backref('thumbnail_match_results', lazy=True, cascade='delete'))
    tags = db.relationship(
        'Tag', secondary=match_result_tags, lazy='subquery',
        backref=db.backref('match_results', lazy=True))

    def __repr__(self):
        templ = \
            '<MatchResult:{0.id} url:[{0.url.value}] t_url:[{1}] tags:{2}>'
        return templ.format(
            self, self.thumbnail_url.value if self.thumbnail_url else '', len(self.tags))


class Namespace(Base):
    """Namespace model."""
    value = db.Column(db.String, unique=True, nullable=False)
    alias = db.Column(db.String)
    hidden = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Namespace:{0.id} {0.value}>'.format(self)

    @hybrid_property
    def tag_count(self):
        try:
            return len(self.tags) if self.tags else 0
        except TypeError:
            return 0


class Netloc(Base):
    value = db.Column(db.String, unique=True, nullable=False)
    hidden = db.Column(db.Boolean, default=False)


class NamespaceHtmlClass(Base):
    value = db.Column(db.String)
    namespace_id = db.Column(db.Integer, db.ForeignKey('namespace.id'))
    namespace = db.relationship(
        'Namespace', foreign_keys='NamespaceHtmlClass.namespace_id', lazy='subquery',
        backref=db.backref('html_class', lazy=True, cascade='delete'))


class Tag(SingleStringModel):
    """Tag model."""
    namespace_id = db.Column(db.Integer, db.ForeignKey('namespace.id'))
    namespace = db.relationship(
        'Namespace', foreign_keys='Tag.namespace_id', lazy='subquery',
        backref=db.backref('tags', lazy=True, cascade='delete'))
    alias = db.Column(db.String)
    hidden = db.Column(db.Boolean, default=False)

    def __repr__(self):
        templ = '<Tag:{0.id} {0.as_string}>'
        return templ.format(self)

    @property
    def as_string(self):
        nm = '{}:'.format(self.namespace.value) if self.namespace else ''
        return ''.join([nm, self.value])

    @property
    def namespace_value(self):
        if self.namespace and self.namespace.alias:
            return self.namespace.alias
        elif self.namespace:
            return self.namespace.value
        return ''

    def get_html_class(self):
        if not self.namespace:
            return
        val = 'tag-' + self.namespace.value
        val = val.replace(' ', '-')
        if self.namespace.html_class:
            return val + ' ' + ' '.join([x.value for x in self.html_class])
        return val


class SearchImage(Base):
    """Search image"""
    img_checksum = db.Column(db.String)
    img_url = db.Column(URLType)
    # url result
    search_url = db.Column(URLType)
    similar_search_url = db.Column(URLType)
    size_search_url = db.Column(URLType)
    # img guess
    img_guess = db.Column(db.String)


class TextMatch(Base):
    # mostly on every text match obj
    title = db.Column(db.String)
    url = db.Column(URLType)
    url_text = db.Column(db.String)
    text = db.Column(db.String)
    # optional, it also mean there is thumbnail
    imgres_url = db.Column(URLType)
    imgref_url = db.Column(URLType)
    # search image
    search_image_id = db.Column(db.Integer, db.ForeignKey('search_image.id'))
    search_image_model = relationship(
        'SearchImage', foreign_keys='TextMatch.search_image_id', lazy='subquery',
        backref=db.backref('text_matches', lazy=True))
    # image (optional)
    img_id = db.Column(db.Integer, db.ForeignKey('match_result.id'))
    img = db.relationship(
        'MatchResult', foreign_keys='TextMatch.img_id', lazy='subquery',
        backref=db.backref('text_matches', lazy=True))


class MainSimilarResult(Base):
    title = db.Column(db.String)
    search_url = db.Column(URLType)
    search_image_id = db.Column(db.Integer, db.ForeignKey('search_image.id'))
    search_image_model = relationship(
        'SearchImage', foreign_keys='MainSimilarResult.search_image_id', lazy='subquery',
        backref=db.backref('main_similar_results', lazy=True))


class SearchImagePage(Base):
    TYPE_SIMILAR = '1'
    TYPE_SIZE = '2'
    TYPES = [
        (TYPE_SIMILAR, 'Similar'),
        (TYPE_SIZE, 'Size'),
    ]
    page = db.Column(db.Integer, default=1, nullable=False)
    search_type = db.Column(ChoiceType(TYPES))
    search_img_id = db.Column(db.Integer, db.ForeignKey('search_image.id'))
    search_img = db.relationship(
        'SearchImage', foreign_keys='SearchImagePage.search_img_id', lazy='subquery',
        backref=db.backref('pages', lazy=True))
    match_results = db.relationship(
        'MatchResult', secondary=search_image_match_results, lazy='subquery',
        backref=db.backref('search_image_pages', lazy=True))


class Response(Base):
    METHODS = [
        ['get', 'get'],
        ['post', 'post'],
        ['head', 'head'],
    ]
    method = db.Column(ChoiceType(METHODS), nullable=False)
    url_id = db.Column(db.Integer, db.ForeignKey('url.id'), nullable=False)
    url = db.relationship(
        'Url', foreign_keys='Response.url_id', lazy='subquery',
        backref=db.backref('responses', lazy=True))
    kwargs_json = db.Column(JSONType)
    # request result
    status_code = db.Column(db.Integer)
    reason = db.Column(db.String)
    final_url_id = db.Column(db.Integer, db.ForeignKey('url.id'))
    final_url = db.relationship(
        'Url', foreign_keys='Response.final_url_id', lazy='subquery',
        backref=db.backref('on_final_responses', lazy=True))
    text = db.Column(db.String)
    json = db.Column(JSONType)
    links = db.Column(JSONType)
    headers = db.Column(JSONType)
    # requests_html
    #  render = db.Column(db.Boolean)
    #  url_links db.Column()  # NOTE: requests lib may have this too
    #  absolute_links = db.Column()
    #  next_url_id = db.relationship()
    #  next_url = db.relationship

    @classmethod
    def create(
            cls, url, method, session, kwargs_json=None, requests_lib='requests_html',
            render=False, return_response=False,
            on_model_change_func=None, handle_view_exception=None, after_model_change_func=None):
        assert_msg = 'Unknown requests lib: {}'.format(requests_lib)
        assert requests_lib in ('requests', 'requests_html'), assert_msg
        try:
            url_scheme = urlparse(url).scheme
            err_msg = 'Unknown scheme: {}'.format(url_scheme)
            assert urlparse(url).scheme in ('http', 'https'), err_msg
            url_model = get_or_create(session, Url, value=url)[0]
            model = cls(url=url_model, method=method)
            kwargs = {}
            if kwargs_json and kwargs_json.strip():
                kwargs = json.loads(kwargs_json)
            model.kwargs_json = kwargs
            if requests_lib == 'requests_html':
                requests_session = HTMLSession()
                resp = getattr(requests_session, method.lower())(url, **kwargs)
            else:
                resp = requests.request(method, url, **kwargs)
            if requests_lib == 'requests_html' and render:
                resp.html.render()
            # resp to model
            model.headers = resp.headers._store
            model.status_code = resp.status_code
            if resp.url == url:
                final_url_model = url_model
            else:
                with session.no_autoflush:
                    final_url_model = get_or_create(session, Url, value=resp.url)[0]
            model.final_url = final_url_model
            model.text = resp.text
            try:
                model.json = resp.json()
            except json.decoder.JSONDecodeError:
                pass
            model.links = resp.links
            model.reason = resp.reason
            # populate_obj finished
            session.add(model)
            if on_model_change_func:
                on_model_change_func(model)
            session.commit()
        except Exception as ex:
            log.exception('Failed to create record.')
            log.exception('Failed.', url=url, ex=ex)
            if handle_view_exception:
                if not handle_view_exception(ex):
                    flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
            session.rollback()
            if not return_response:
                return False
            else:
                return (False, None)
        else:
            if after_model_change_func:
                after_model_change_func(model)
        if not return_response:
            return model
        return model, resp

    @hybrid_property
    def content_type(self):
        if not hasattr(self.headers, 'get'):
            if not isinstance(self.headers, orm_attributes.InstrumentedAttribute):
                log.debug('headers dont have get get attr, type:{}'.format(
                    type(self.headers)))
            return
        ct = self.headers.get('content-type', [None, None])[1]
        if ct:
            return [x.strip() for x in ct.split(';')]


class Plugin(Base):

    path = db.Column(db.String)
    name = db.Column(db.String)
    version = db.Column(db.String)
    description = db.Column(db.String)
    author = db.Column(db.String)
    website = db.Column(URLType)
    copyright = db.Column(db.String)
    categories = db.Column(ScalarListType)
    category = db.Column(db.String)

    def __repr__(self):
        templ = '<Plugin:{0.id} category:{0.category} name:[{0.name}] v:{0.version}>'
        return templ.format(self)


def get_or_create_match_result(session, url, thumbnail_url=None, **kwargs):
    url_model = get_or_create(session, Url, value=url)[0]
    if not thumbnail_url:
        instance, created = get_or_create(session, MatchResult, url=url_model, **kwargs)
        return instance, created
    thumbnail_url_model = get_or_create(session, Url, value=thumbnail_url)[0]
    instance, created = get_or_create(
        session, MatchResult, url=url_model, thumbnail_url=thumbnail_url_model, **kwargs)
    # NOTE may create redundant match result with empty thumbnail
    return instance, created


def get_or_create(session, model, **kwargs):
    """Creates an object or returns the object if exists."""
    instance = session.query(model).filter_by(**kwargs).first()
    created = False
    if not instance:
        instance = model(**kwargs)
        session.add(instance)
        created = True
    return instance, created

# ## plugin


def get_plugin_manager():
    manager = PluginManager(plugin_info_ext='ini')
    manager.setCategoriesFilter({
        'mode': ModePlugin,
    })
    manager.setPluginPlaces([plugin.__path__[0]])
    manager.collectPlugins()
    return manager


class ModePlugin(IPlugin):
    """Base class for parser plugin."""

    def get_match_results(
            self, search_term=None, page=1, text=None, response=None, session=None, url=None):
        """Get match result models.

        - search_term and page
        - text or response or both
        """
        raise NotImplementedError

    @classmethod
    def get_match_results_dict(self, text=None, response=None, session=None, url=None):
        """main function used for plugin.

        Returns:
            dict: match results data

        Examples:
            get match results dict.

            >>> print(ParserPlugin.get_match_results_dict(text=text)
            {
                'url': {
                    'http:example.com/1.html': {
                        'thumbnail': [
                            'http:example.com/1.jpg',
                            'http:example.com/1.png',
                            ...
                        ],
                        'tag': [
                            (None, 'tag_value1'),
                            ('namespace1', 'tag_value2', ...)
                        ],
                    },
                    ...
                },
                'tag': [(None, 'tag_value3'), ('namespace2', 'tag_value4'), ...]
            }
        """
        return {}

    @classmethod
    def match_results_models_from_dict(cls, dict_input, session):
        if dict_input['tag']:
            pass
        for url, data in dict_input['url'].items():
            tag_models = []
            for nm, tag_value in data['tag']:
                #  tag_model = models.get_or_create_tag()
                if nm:
                    nm_model = get_or_create(session, Namespace, value=nm)[0]
                    tag_models.append(get_or_create(
                        session, Tag, value=tag_value, namespace=nm_model)[0])
                else:
                    tag_models.append(get_or_create(
                        session, Tag, value=tag_value, namespace=None)[0])
                pass
            mr_model = None
            if data['thumbnail']:
                for tu in data['thumbnail']:
                    mr_model = get_or_create_match_result(
                        session, url=url, thumbnail_url=tu)[0]
                    yield mr_model
            else:
                mr_model = get_or_create_match_result(session, url=url)[0]
                yield mr_model
            mr_model.url.tags.extend(tag_models)
