"""Admin module."""
from urllib.parse import urljoin
import textwrap

from flask import request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import BaseSQLAFilter
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
            session = models.db.session
            model, created = api.get_or_create_search_query(
                query, page, disable_cache=disable_cache, session=session)
            model.match_results = [x for x in model.match_results if x]
            models.db.session.commit()
            pagination_kwargs['per_page'] = 1
            pagination_kwargs['total'] = \
                models.SearchQuery.query.join(models.SearchQuery.search_term).filter(
                    models.SearchTerm.value == query).count()
            template_kwargs['entry'] = model
            template_kwargs['match_results'] = [
                x for x in model.match_results if not x.img_url.filtered]
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
        'search_term':
        lambda v, c, m, p:
        Markup('<a href="{}">{}</a>'.format(
            url_for('admin.index', query=m.search_term.value),
            m.search_term.value
        )),
        'page':
        lambda v, c, m, p:
        Markup('<a href="{}">{}</a>'.format(
            url_for('admin.index', query=m.search_term.value, page=m.page),
            m.page
        )),
    }
    column_list = ('created_at', 'search_term', 'page')
    column_searchable_list = ('page', 'search_term.value')
    column_sortable_list = ('created_at', ('search_term', 'search_term.value'), 'page')
    column_filters = ('page', 'search_term.value')


class FilterMatchResultSearchQuery(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        res = query.filter(
            self.column.search_queries.contains(models.SearchQuery.query.get(value)))
        return res

    def operation(self):
        return 'equal'

    def get_options(self, view):
        return [
            (str(x.id), "'{}' page:{}".format(x.search_term.value, x.page))
            for x in models.SearchQuery.query.all()
        ]


class FilterMatchResultFilteredUrl(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        # __import__('pdb').set_trace()
        furl_res = query.join('img_url').filter(models.ImageUrl.filtered)
        if value == '1':
            res = furl_res
        else:
            res = query.filter(
                models.MatchResult.id.notin_([x.id for x in furl_res.all() if hasattr(x, 'id')]))
        return res

    def operation(self):
        return 'in filter list'


class MatchResultView(CustomModelView):
    """Custom view for MatchResult model."""

    @staticmethod
    def format_entry(m):
        figcaption_templ = """
        <a class="icon btn btn-default btn-xs" href="{}">
        <span class="fa fa-eye glyphicon glyphicon-eye-open"></span>
        image url
        </a>"""
        templ = '<figure><a href="{1}"><img src="{0}"></a><figcaption>{2}</figcaption></figure>'
        field = m.img_url if m.img_url else m.thumbnail_url
        figcaption = figcaption_templ.format(
            url_for('imageurl.details_view', id=field.id, url=url_for('matchresult.index_view')))
        return Markup(templ.format(m.thumbnail_url.url, field.url, figcaption))

    @staticmethod
    def format_img_url(m, p):
        data = getattr(m, p)
        return Markup("""
            <a href={1}>ID:{0.id}, size:{0.width}x{0.height}</a><br/>
            <a href="{0.url}">{0.url}</a>
            """.format(
            data,
            url_for('imageurl.details_view', id=data.id),
        ))

    column_formatters = {
        'created_at': date_formatter,
        'Entry': lambda v, c, m, p: MatchResultView.format_entry(m),
        'img_url': lambda v, c, m, p: MatchResultView.format_img_url(m, p),
        'thumbnail_url': lambda v, c, m, p: MatchResultView.format_img_url(m, p),
        'w': lambda v, c, m, p: m.img_url.width,
        'h': lambda v, c, m, p: m.img_url.height,
    }
    column_filters = [
        FilterMatchResultSearchQuery(column=models.MatchResult, name='search query'),
        FilterMatchResultFilteredUrl(
            column=models.MatchResult, name='url filtered',
            options=(('1', 'yes'), ('0', 'no'))
        )
    ]
    column_list = ('created_at', 'w', 'h', 'Entry')
    column_sortable_list = ('created_at', ('w', 'img_url.width'), ('h', 'img_url.height'))
    can_view_details = True
    page_size = 100


class JsonDataView(CustomModelView):
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


class FilterThumbnail(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column.thumbnail_match_results.any())
        else:
            return query.filter(~self.column.thumbnail_match_results.any())

    def operation(self):
        return 'is thumbnail'


class ImageUrlView(CustomModelView):
    """Custom view for ImageURL model."""

    def _url_formatter(self, context, model, name):
        data = getattr(model, name)
        templ = """
        <a href="{0}">{0}</a><br/>
        <a href="{0}">[link]</a>
        """
        return Markup(templ.format(data))

    column_searchable_list = ('url', 'width', 'height')
    column_filters = ('width', 'height')
    column_formatters = {'created_at': date_formatter, 'url': _url_formatter, }
    inline_models = (models.Tag, models.FilteredImageUrl,)
    details_template = 'gbooru_images_download/image_url_details.html'
    column_filters = [
        'width',
        'height',
        FilterThumbnail(
            models.ImageUrl, 'Thumbnail', options=(('1', 'Yes'), ('0', 'No'))
        )
    ]


class TagView(CustomModelView):
    """Custom view for Tag model."""

    column_filters = ('value', 'namespace.value')
    column_formatters = {'created_at': date_formatter, }
    column_labels = {'created_at': 'Created At', 'namespace.value': 'Namespace', 'name': 'Name'}
    column_list = ('created_at', 'namespace.value', 'value')
    column_searchable_list = ('value', 'namespace.value')
    column_sortable_list = ('value', 'namespace.value', 'created_at')


class FilteredImageUrlView(CustomModelView):
    """Custom view for Tag model."""

    column_formatters = {'created_at': date_formatter, }

    def create_form(self):
        form = super().create_form()
        ImageUrl = models.ImageUrl
        if ('img_id') in request.args.keys():
            img_url_m = self.session.query(ImageUrl).filter(ImageUrl.id == request.args['img_id']).one()  # NOQA
            form.img_url.data = img_url_m
        return form


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
        if not model.img_guess:
            return Markup('')
        else:
            return Markup('<a href={}>{}</a>'.format(
                url_for('admin.index', query=model.img_guess), model.img_guess))

    column_formatters = {
        'created_at': date_formatter,
        'Result': _result_formatter,
        'img_guess': _img_guess_formatter,
        'img_url':
            lambda v, c, m, p: Markup('<a href="{0}">{0}</a>'.format(
                m.img_url.url,
            ) if m.img_url else ''),
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
    column_exclude_list = ('search_url', 'similar_search_url', 'size_search_url' )  # NOQA
    column_searchable_list = ('img_url.url', )
    column_list = ('created_at', 'img_url', 'img_guess', 'Result')


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
