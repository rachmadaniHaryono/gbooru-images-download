"""Admin module."""
from urllib.parse import urljoin
import textwrap

from flask import request, url_for
from flask_admin.contrib.sqla import ModelView
from jinja2 import Markup
import humanize
import structlog

from . import models


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


class CustomModelView(ModelView):
    can_view_details = True
    page_size = 100
    column_default_sort = ('created_at', True)


class JsonDataView(CustomModelView):
    """Custom view for json data model"""

    can_view_details = True

    def _value_formatter(view, context, model, name):
        res = ''
        for key, value in model.value.items():
            if not value:
                continue
            res += '<tr><th>{0}</th><td>{1}</td></tr>'.format(key, value)
        res = '<table class="table table-bordered table-condensed">{}</table>'.format(res)
        return Markup(res)
    column_formatters = {'created_at': date_formatter, 'value': _value_formatter, }


class FilteredImageUrlView(CustomModelView):
    """Custom view for Tag model."""

    can_edit = False
    can_view_details = False
    can_export = True
    column_formatters = {
        'created_at': date_formatter,
        'img_url.id': lambda v, c, m, p:
            Markup(
                '<a href="{0}">{1}</a>'.format(
                    url_for('url.details_view', id=m.img_url.id),
                    m.img_url.id,
                )
            ),
        'img': lambda v, c, m, p:
            Markup(
                '<img style="{1}" '
                'src="{0}">'.format(
                    m.img_url.match_results[0].thumbnail_url.value,
                    ' '.join([
                        'max-width:100px;',
                        'display: block;',
                        'margin-left: auto;',
                        'margin-right: auto;',
                    ])
                )
            ),
        'img_url': lambda v, c, m, p:
            Markup('<a href="{0.value}">{0.value}</a>'.format(m.img_url,)),
    }
    column_labels = {'img_url.id': 'id', 'img_url.width': 'w', 'img_url.height': 'h'}
    column_list = ('created_at', 'img_url.id', 'img', 'img_url', 'img_url.width', 'img_url.height')
    column_sortable_list = ('created_at', 'img_url', 'img_url.width', 'img_url.height')

    def create_form(self):
        form = super().create_form()
        if ('img_id') in request.args.keys():
            img_url_m = self.session.query(
                models.ImageUrl).filter(models.Url.id == request.args['img_id']).one()  # NOQA
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
                m.img_url.value,
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
