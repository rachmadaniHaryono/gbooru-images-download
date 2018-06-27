import json

from flask import flash, make_response, redirect, request, url_for
from flask_admin.babel import gettext
from flask_admin.base import expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from jinja2 import Markup
from wtforms import fields, validators
import humanize
import structlog

from . import api, models


log = structlog.getLogger(__name__)


def date_formatter(view, context, model, name):
    date_data = getattr(model, name)
    humanized_date_data = humanize.naturaltime(date_data)
    return Markup(
        '<span data-toogle="tooltip" title="{}">{}</span>'.format(
            date_data, humanized_date_data
        )
    )


class ResponseView(ModelView):

    def _url_formatter(self, context, model, name):
        data = getattr(model, name)
        templ = '<a href="{0}">{0}</a>'
        return Markup(templ.format(data.value))

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
    column_formatters = {
        'url': _url_formatter,
        'final_url': _url_formatter,
        'method': lambda v, c, m, p: getattr(m, p).value,
        'created_at': date_formatter,
        'text': _text_formatter,
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

    def _url_formatter(self, context, model, name):
        data = getattr(model, name)
        templ = '<a href="{0}">{0}</a>'
        return Markup(templ.format(data.value))

    can_edit = False
    can_delete = False
    can_view_details = True
    column_default_sort = ('created_at', True)
    column_formatters = {
        'created_at': date_formatter,
        'website': lambda v, c, m, p: Markup(
            '<a href="{0}">{0}</a>'.format(getattr(m, p))
        ),
    }
    column_list = ('created_at', 'name', 'version', 'categories', 'description')
    list_template = 'gbooru_images_download/plugin_list.html'

    @expose('/update')
    def index_update_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        manager = api.get_plugin_manager()
        keys = ['name', 'version', 'description', 'author', 'website', 'copyright', 'categories']
        for plugin in manager.getAllPlugins():
            with self.session.no_autoflush:
                model = models.get_or_create(self.session, self.model, module=plugin.path)[0]
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
