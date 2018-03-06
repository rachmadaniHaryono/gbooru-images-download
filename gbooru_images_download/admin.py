"""Admin module."""
from urllib.parse import urljoin
import textwrap

from flask import request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_paginate import get_page_parameter, Pagination
from jinja2 import Markup
import humanize
import structlog

from gbooru_images_download import forms, models, api


log = structlog.getLogger(__name__)


def date_formatter(_, __, model, name):
    date_data = getattr(model, name)
    humanized_date_data = humanize.naturaltime(date_data)
    return Markup(
        '<span data-toogle="tooltip" title="{}">{}</span>'.format(
            date_data, humanized_date_data
        )
    )


def filesize_formatter(_, __, model, name):
    data = getattr(model, name)
    if data:
        return Markup(humanize.naturalsize(data))
    return Markup('')


def get_anchor_tag(url):
    return Markup('<a href="{}">{}</a>'.format(url, '<br>'.join(textwrap.wrap(url))))


class HomeView(AdminIndexView):
    @expose('/')
    def index(self):
        form = forms.IndexForm(request.args)
        page = request.args.get(get_page_parameter(), type=int, default=1)
        query = form.query.data
        disable_cache = form.disable_cache.data
        template_kwargs = {'entry': None, 'query': query, 'form': form, }
        pagination_kwargs = {'page': page, 'show_single_page': False, 'bs_version': 3, }
        if query:
            pagination_kwargs['per_page'] = 1
            model, created = api.get_or_create_search_query(
                query, page, disable_cache=disable_cache)
            if created or disable_cache:
                models.db.session.add(model)
                models.db.session.commit()
            pagination_kwargs['total'] = \
                models.SearchQuery.query.filter(models.SearchQuery.search_query == query).count()
            template_kwargs['entry'] = model
        template_kwargs['pagination'] = Pagination(**pagination_kwargs)
        return self.render('gbooru_images_download/index.html', **template_kwargs)


class CustomModelView(ModelView):
    can_view_details = True
    page_size = 100
    column_default_sort = ('created_at', True)


class SearchQueryView(CustomModelView):
    """Custom view for SearchQuery model."""
    column_formatters = {
        'created_at': date_formatter,
        'search_query':
        lambda v, c, m, p:
        Markup('<a href="{}">{}</a>'.format(
            url_for('admin.index', query=m.search_query),
            m.search_query
        )),
        'page':
        lambda v, c, m, p:
        Markup('<a href="{}">{}</a>'.format(
            url_for('admin.index', query=m.search_query, page=m.page),
            m.page
        )),
    }
    column_searchable_list = ('page', 'search_query')
    column_filters = ('page', 'search_query')


class MatchResultView(CustomModelView):
    """Custom view for MatchResult model."""

    def _image_formatter(view, context, model, name):
        desc_table = '<tr><th>Title</th><td>{}</td></tr>'.format(model.picture_title)
        if model.picture_subtitle:
            desc_table += '<tr><th>Subtitle</th><td>{}</td></tr>'.format(model.picture_subtitle)
        desc_table += '<tr><th>Site</th><td><a href="https://{0}">{0}</a></td></tr>'.format(
            model.site)
        desc_table += '<tr><th>Site title</th><td>{}</td></tr>'.format(model.site_title)
        desc_table = '<table class="table table-condensed table-bordered">{}</table>'.format(
            desc_table)
        template = '<a href="{1}"><img class="img-responsive center-block" src="{0}"></a><br>{2}'
        return Markup(template.format(model.thumb_url, model.img_url, desc_table))

    @staticmethod
    def format_thumbnail(m):
        templ = '<a href="{1}"><img src="{0}"></a>'
        if m.img_url:
            return Markup(templ.format(m.thumbnail_url.url, m.img_url.url))
        return Markup(templ.format(m.thumbnail_url.url, m.thumbnail_url.url))

    @staticmethod
    def format_json_data(json_data):
        return Markup('<p><a href="{}">{}</a></p>'.format(
            url_for('jsondata.details_view', id=json_data.id), Markup.escape(json_data)))  # NOQA

    @staticmethod
    def format_search_query(search_query):
        return Markup('<p><a href="{}">{}</a></p>'.format(
            url_for('searchquery.details_view', id=search_query.id), Markup.escape(search_query)))

    def _imgref_url_formatter(view, context, model, name):
        res = Markup('<p>{}</p>'.format(get_anchor_tag(model.imgref_url))) if model.imgref_url else ''  # NOQA
        res += Markup('<p>{}</p>'.format(MatchResultView.format_thumbnail(model)))
        if model.search_query:
            res += MatchResultView.format_search_query(model.search_query)
        res += MatchResultView.format_json_data(model.json_data)
        return res

    column_formatters = {
        'created_at': date_formatter,
        'json_data': lambda v, c, m, p: MatchResultView.format_json_data(m.json_data),
        'search_query': lambda v, c, m, p: MatchResultView.format_search_query(m.search_query) if m.search_query else '',  # NOQA
        'thumbnail_url': lambda v, c, m, p: MatchResultView.format_thumbnail(m),
        'imgref_url': _imgref_url_formatter,
        'imgres_url': lambda v, c, m, p: get_anchor_tag(m.imgres_url) if m.imgres_url else '',
        'img_url': lambda v, c, m, p:
        Markup("""
            <p><a href={1}>ID:{0.id},size:{0.width}x{0.height}</a></p>
            <p><a href="{0.url}">{2}</a></p>""".format(
            m.img_url,
            url_for('imageurl.details_view', id=m.img_url.id),
            '<br>'.join(textwrap.wrap(m.img_url.url))
        )),
    }
    column_exclude_list = ('imgres_url', 'img_url', 'thumbnail_url', 'search_query', 'json_data')
    column_searchable_list = ('imgref_url', 'search_query.search_query')
    can_view_details = True
    page_size = 100


class JSONDataView(CustomModelView):
    """Custom view for json data model"""
    def _value_formatter(view, context, model, name):
        res = ''
        for key, value in model.value.items():
            if not value:
                continue
            res += '<tr><th>{0}</th><td>{1}</td></tr>'.format(key, value)
        res = '<table class="table table-bordered table-condensed">{}</table>'.format(res)
        return Markup(res)
    column_formatters = {'created_at': date_formatter, 'value': _value_formatter, }


class ImageURLView(CustomModelView):
    """Custom view for ImageURL model."""

    def _url_formatter(view, context, model, name):
        match_results = model.match_results
        templ = """
        <figure>
        <a href="{3}"><img src="{1}"></a>
        <figcaption><a href="{0}">{2}</figcaption>
        <figure>"""
        img_view_url = url_for('u.index', u=model.url)
        if match_results:
            first_match_result = next(iter(match_results or []), None)
            shorted_url = '<br>'.join(textwrap.wrap(model.url))
            return Markup(
                templ.format(
                    model.url,
                    first_match_result.thumbnail_url.url,
                    shorted_url,
                    img_view_url
                )
            )
        shorted_url = '<br>'.join(textwrap.wrap(model.url))
        return Markup(templ.format(model.url, model.url, shorted_url, img_view_url))

    column_searchable_list = ('url', 'width', 'height')
    column_filters = ('width', 'height')
    column_formatters = {'created_at': date_formatter, 'url': _url_formatter, }
    form_ajax_refs = {'tags': {'fields': ['namespace', 'name'], 'page_size': 10}}


class TagView(CustomModelView):
    """Custom view for Tag model."""

    column_searchable_list = ('namespace', 'name')
    column_filters = ('namespace', 'name')
    column_formatters = {'created_at': date_formatter, }


class ImageFileView(CustomModelView):
    """Custom view for ImageFile model."""

    @staticmethod
    def _format(thumbnail):
        return Markup("""
            <p>Thumbnail:
            <a href="{}">{}</a>
            <a href="{}"><span class="fa fa-pencil glyphicon glyphicon-pencil"></span></a>
            </p>""".format(
            url_for('imagefile.details_view', id=thumbnail.id),
            Markup.escape(str(thumbnail)),
            url_for('imagefile.edit_view', id=thumbnail.id)
        ))

    def _checksum_formatter(view, context, model, name):
        shorted_checksum = Markup('<p>Checksum:' + '<br>'.join(textwrap.wrap(model.checksum)) + '</p>')  # NOQA
        if not model.thumbnail:
            return shorted_checksum
        thumbnail_a_tag = Markup("""
            <p>Thumbnail:
            <a href="{}">{}</a>
            <a href="{}"><span class="fa fa-pencil glyphicon glyphicon-pencil"></span></a>
            </p>""".format(
            url_for('imagefile.details_view', id=model.thumbnail.id),
            Markup.escape(str(model.thumbnail)),
            url_for('imagefile.edit_view', id=model.thumbnail.id)
        ))
        figcaption = shorted_checksum + thumbnail_a_tag
        return Markup('<figure><img src="{}"><figcaption>{}</figcaption></figure>'.format(
            url_for('thumbnail', filename=model.thumbnail.checksum + '.jpg'),
            figcaption
        ))

    column_formatters = {
        'created_at': date_formatter,
        'size': filesize_formatter,
        'checksum': _checksum_formatter
    }
    column_exclude_list = ('thumbnail',)


class SearchImageView(CustomModelView):
    """Custom view for SearchImage model."""

    def _result_formatter(view, context, model, name):
        res = '<a href="{}">main</a>'.format(model.search_url)
        if model.size_search_url:
            res += ', <a href="{}">size</a>'.format(model.size_search_url)
        if model.similar_search_url:
            res += ', <a href="{}">similar</a>'.format(model.similar_search_url)
        return Markup(res)

    def _img_guess_formatter(view, context, model, name):
        res = '<p>Image guess: {}</p>'.format(
            Markup('<a href={}>{}</a>'.format(
                url_for('admin.index', query=model.img_guess), model.img_guess))
        ) if model.img_guess else ''
        if model.searched_img_url:
            res += '<p>Searched Url:</p>'
            res += '<a href="{}">{}</a>'.format(
                model.searched_img_url,
                '<br>'.join(textwrap.wrap(model.searched_img_url)))
        return Markup(res)

    column_formatters = {
        'created_at': date_formatter,
        'Result': _result_formatter,
        'img_guess': _img_guess_formatter,
        'search_url':
            lambda v, c, m, p: Markup('<a href="{1}">{0}</a>'.format(
                Markup('<br>'.join(textwrap.wrap(m.search_url))),
                m.search_url
            )),
        'similar_search_url':
            lambda v, c, m, p: Markup('<a href="{1}">{0}</a>'.format(
                Markup('<br>'.join(textwrap.wrap(m.similar_search_url))),
                m.similar_search_url
            )) if m.similar_search_url else Markup(''),
        'size_search_url':
            lambda v, c, m, p: Markup('<a href="{1}">{0}</a>'.format(
                Markup('<br>'.join(textwrap.wrap(m.size_search_url))),
                m.size_search_url
            )) if m.size_search_url else Markup(''),
    }
    column_exclude_list = ('search_url', 'similar_search_url', 'size_search_url', 'searched_img_url', )  # NOQA
    column_searchable_list = ('searched_img_url', )
    column_list = ('created_at', 'searched_img_url', 'img_guess', 'Result')


class SearchImagePageView(CustomModelView):
    """Custom view for SearchImagePage model."""

    column_formatters = dict(
        created_at=date_formatter,
        search_type=lambda v, c, m, p: m.search_type.value
    )
    column_exclude_list = ('search_url', 'similar_search_url', 'size_search_url', )


class TextMatchView(CustomModelView):
    """Custom view for TextMatch model."""

    column_formatters = {
        'created_at': date_formatter,
        'content': lambda v, c, m, p: Markup(
            """<h4>{0}</h4>
            <div>
                <p>{1}</p>
                <a href="{2}">{4}</a>
                <p>{3}</p>
            </div>""".format(
                m.title,
                '<br>'.join(textwrap.wrap(m.text)),
                m.url,
                m.url_text,
                '<br>'.join(textwrap.wrap(m.url)),
            )
        ),
    }
    column_searchable_list = ('url', 'url_text', 'text', 'title')
    column_filters = ('url_text', 'text', 'title')
    column_exclude_list = ('imgres_url', 'imgref_url')
    column_list = (
        'search_image_model',
        'created_at',
        'content',
    )


class MainSimilarResultView(CustomModelView):
    """Custom view for Main similar result view model."""

    column_formatters = dict(
        created_at=date_formatter,
        title=lambda v, c, m, p: Markup('<a href="{0}">{0}</a>'.format(m.title)),
        search_url=lambda v, c, m, p: Markup('<a href="{0}">{1}</a>'.format(
            urljoin('https://www.google.com', m.search_url),
            Markup('<br>'.join(textwrap.wrap(m.search_url)))
        )),
    )
    column_exclude_list = ('search_url', )
    column_searchable_list = ('title', )
    column_filters = ('title', )
