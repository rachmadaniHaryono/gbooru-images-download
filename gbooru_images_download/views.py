import json
from urllib.parse import unquote, urlparse

from flask import flash, make_response, redirect, request, url_for
from sqlalchemy.sql.expression import desc
from flask_admin.babel import gettext
from flask_admin.form import rules
from flask_admin.base import expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from jinja2 import Markup
from wtforms import fields, validators
import humanize
import structlog

from . import api, models, filters


log = structlog.getLogger(__name__)


def date_formatter(view, context, model, name):
    date_data = getattr(model, name)
    humanized_date_data = humanize.naturaltime(date_data)
    return Markup(
        '<span data-toogle="tooltip" title="{}">{}</span>'.format(
            date_data, humanized_date_data
        )
    )


def url_formatter(view, context, model, name):
    data = getattr(model, name)
    if not data:
        return ''
    templ = '<a href="{0}">{1}</a>'
    return Markup(templ.format(data.value, unquote(str(data.value))))


class ResponseView(ModelView):

    def _text_formatter(self, context, model, name):
        return_url = get_redirect_target() or self.get_url('.index_view')
        data = getattr(model, name)
        code_section = '<pre><code class="language-html">{}</code></pre>'.format(
            Markup.escape(data)
        )
        button = ''
        if data.strip():
            button = '<a class="btn btn-default" href="{}">view text</a>'.format(
                url_for('.details_text_view', id=model.id, url=return_url)
            )
        return Markup('{}<br/>{}'.format(button, code_section))

    can_edit = False
    can_view_details = True
    column_default_sort = ('created_at', True)
    column_filters = [
        'created_at',
        'final_url',
        'status_code',
        'text',
        'url',
    ]
    column_formatters = {
        'created_at': date_formatter,
        'final_url': url_formatter,
        'headers': lambda v, c, m, p: Markup(
            '<pre><code {1} style="{2}">{0}</code></pre>'.format(
                json.dumps(getattr(m, p), indent=1),
                'class="language-json"',
                ' '.join([
                    'white-space: pre-wrap;',
                    'white-space: -moz-pre-wrap;',
                    'white-space: -pre-wrap;',
                    'white-space: -o-pre-wrap;',
                    'word-wrap: break-word;',
                ])
            )),
        'method': lambda v, c, m, p: getattr(m, p).value,
        'text': _text_formatter,
        'url': url_formatter,
    }
    column_list = ('created_at', 'status_code', 'method', 'url', 'content_type')
    details_template = 'gbooru_images_download/response_details.html'
    form_columns = ('method', 'kwargs_json')
    form_create_rules = ('url_input', 'method', 'kwargs_json')
    form_overrides = {
        'url_input': fields.StringField, 'kwargs_json': fields.TextAreaField, }
    form_widget_args = {
        'method': {'class': 'radio'},
        'kwargs_json': {'rows': 5},
    }

    def get_create_form(self):
        form = super().get_form()

        def json_check(form, field):
            data = form.data.strip()
            if data:
                try:
                    json.loads(form.data)
                except Exception as e:
                    message = 'Json check failed: {}'.format(str(e))
                    raise validators.ValidationError(message)

        form.kwargs_json.kwargs['validators'].append(json_check)
        # RadioField can't be created on form_overrides
        # it need choices list to at init
        form.method = fields.RadioField(
            'Method', [validators.required()],
            choices=[('head', ' head'), ('post', 'post'), ('get', 'get')])
        form.url_input = fields.StringField(
            'Url', [validators.required(), validators.URL()])
        return form

    def create_model(self, form):
        model = self.model.create(
            url=form.url_input.data, method=form.method.data, session=self.session,
            kwargs_json=form.kwargs_json.data,
            on_model_change_func=lambda x: self._on_model_change(form, x, True),
            handle_view_exception=self.handle_view_exception,
            after_model_change_func=lambda x: self.after_model_change(form, x, True)
        )
        return model

    @expose('/details/text')
    def details_text_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)
        model = self.get_one(id)
        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)
        resp = make_response(model.text)
        resp.mimetype = model.content_type
        return resp


class PluginView(ModelView):

    can_edit = False
    can_delete = False
    can_create = False
    can_view_details = True
    column_default_sort = ('created_at', True)
    column_filters = [
        'category',
        'created_at',
        'description',
        'name',
        'version',
    ]
    column_formatters = {
        'created_at': date_formatter,
        'website': lambda v, c, m, p: Markup(
            '<a href="{0}">{0}</a>'.format(getattr(m, p))
        ),
        'path': lambda v, c, m, p: Markup(
            '<pre style="{1}">{0}</pre>'.format(
                getattr(m, p),
                ' '.join([
                    'white-space: pre-wrap;',
                    'white-space: -moz-pre-wrap;',
                    'white-space: -pre-wrap;',
                    'white-space: -o-pre-wrap;',
                    'word-wrap: break-word;',
                ])
            )
        ),
        'category': lambda v, c, m, p: Markup(
            '<a href="{}">{}</a>'.format(
                url_for('plugin.index_view', flt2_2=getattr(m, p)),
                getattr(m, p)
            )
        ),
    }
    column_list = ('created_at', 'name', 'version', 'category', 'description')
    details_modal = True
    list_template = 'gbooru_images_download/plugin_list.html'

    @expose('/update')
    def index_update_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        manager = api.get_plugin_manager()
        keys = [
            'name', 'version', 'description', 'author', 'website', 'copyright',
            'categories', 'category']
        for plugin in manager.getAllPlugins():
            with self.session.no_autoflush:
                model = models.get_or_create(self.session, self.model, path=plugin.path)[0]
            #  update record
            for key in keys:
                if getattr(plugin, key):
                    if key == 'version':
                        setattr(model, key, str(getattr(plugin, key)))
                    else:
                        setattr(model, key, getattr(plugin, key))
            self.session.add(model)
        self.session.commit()
        return redirect(return_url)


class MatchResultView(ModelView):

    def _order_by(self, query, joins, sort_joins, sort_field, sort_desc):
        try:
            res = super()._order_by(query, joins, sort_joins, sort_field, sort_desc)
        except AttributeError as e:
            if sort_field.key not in ('url', 'thumbnail_url'):
                log.error('{}'.format(e), sort_field_key=sort_field.key)
                raise e
            if sort_field is not None:
                # Handle joins
                query, joins, alias = self._apply_path_joins(
                    query, joins, sort_joins, inner_join=False)
                try:
                    field = getattr(self.model, sort_field.key)
                    if sort_desc:
                        query = query.join(models.Url, field).order_by(desc(models.Url.value))
                    else:
                        query = query.join(models.Url, field).order_by(models.Url.value)
                except Exception as e:
                    raise e
            return query, joins
        return res

    def _url_formatter(self, context, model, name):
        data = getattr(model, name)
        res = '(ID:{}) '.format(data.id)
        res += url_formatter(self, context, model, name)
        return res

    can_view_details = True
    can_set_page_size = True
    column_default_sort = ('created_at', True)
    column_filters = [
        'created_at',
        'tags',
        'thumbnail_url',
        'url',
    ]
    column_formatters = {
        'created_at': date_formatter,
        'thumbnail_url': url_formatter,
        'url': _url_formatter,
    }
    column_sortable_list = ('created_at', 'url', 'thumbnail_url')
    page_size = 100

    def create_model(self, form):
        try:
            models.get_or_create_match_result(
                self.session, url=form.url, thumbnail_url=form.thumbnail_url)
            model = self.model()
            form.populate_obj(model)
            # plugin.get_match_results(search_term, page, session)
            assert model.mode.category == 'mode'
            pm = api.get_plugin_manager()
            plugin = pm.getPluginByName(model.mode.name, model.mode.category)
            mrs = list(set(plugin.plugin_object.get_match_results(
                model.search_term, model.page, self.session)))
            model.match_results = mrs
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                log.exception('Failed to create record.')
            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, True)
        return model


class NetlocView(ModelView):
    can_create = False


    def get_list(self, page, sort_field, sort_desc, search, filters, page_size=None):
        res = super().get_list(page, sort_field, sort_desc, search, filters, page_size=None)
        return res


class SearchQueryView(ModelView):
    """Custom view for SearchQuery model."""

    def _search_term_formatter(self, context, model, name):
        data = getattr(model, name)
        parsed_data = urlparse(data)
        if parsed_data.netloc and parsed_data.scheme in ('http', 'https'):
            return Markup('<a href="{0}">{0}</a>'.format(data))
        return data

    column_formatters = {
        'created_at': date_formatter,
        'page':
        lambda v, c, m, p:
        Markup('<a href="{}">{}</a>'.format(
            url_for('admin.index', query=m.search_term, page=m.page),
            m.page
        )),
        'match result':
        lambda v, c, m, p: len(m.match_results),
        'search_term': _search_term_formatter,
    }
    column_list = ('created_at', 'search_term', 'page', 'match result')
    column_searchable_list = ('page', 'search_term')
    column_sortable_list = ('created_at', 'search_term', 'page')
    column_filters = ('page', 'search_term')
    form_excluded_columns = ['created_at', ]

    def create_model(self, form):
        """
            Create model from form.

            :param form:
                Form instance
        """
        try:
            model = self.model()
            form.populate_obj(model)
            # plugin.get_match_results(search_term, page, session)
            assert model.mode.category == 'mode'
            pm = api.get_plugin_manager()
            plugin = pm.getPluginByName(model.mode.name, model.mode.category)
            try:
                mrs = list(set(plugin.plugin_object.get_match_results(
                    model.search_term, model.page, self.session)))
            except AssertionError as ex:
                if not self.handle_view_exception(ex):
                    flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                    log.exception('Failed to create record.')
                self.session.rollback()
                return False
            model.match_results.extend(mrs)
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except (Exception, AssertionError) as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                log.exception('Failed to create record.')
            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, True)
        return model


class UrlView(ModelView):
    """Custom view for ImageURL model."""

    def _content_type_formatter(self, context, model, name):
        data = list(getattr(model, name))
        if data:
            return ', '.join(data)

    can_view_details = True
    can_set_page_size = True
    column_display_pk = True
    column_filters = [
        'created_at',
        filters.FilteredImageUrl(
            models.Url, 'Filter list', options=(('1', 'Yes'), ('0', 'No')),
        ),
        filters.TagFilter(models.Url, 'Tag')
    ]
    column_formatters = {
        'created_at': date_formatter,
        'value': lambda v, c, m, p: Markup('<a href="{0}">{0}</a>'.format(getattr(m, p))),
        'content_type': _content_type_formatter,
    }
    column_list = ('created_at', 'id', 'value', 'content_type')
    column_searchable_list = ('value', )
    form_edit_rules = [
        rules.FieldSet(('value', 'tags'), 'Url'),
        rules.FieldSet(('match_results', 'thumbnail_match_results'), 'Match Result'),
        rules.FieldSet(('responses', 'on_final_responses'), 'Response'),
    ]
    form_excluded_columns = ['created_at', ]
    form_overrides = dict(value=fields.StringField,)
    page_size = 100
