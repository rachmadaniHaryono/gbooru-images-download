import json

from flask_admin.contrib.sqla import ModelView
from jinja2 import Markup
from wtforms import fields, validators
import humanize
import structlog


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

    can_edit = False
    can_view_details = True
    column_default_sort = ('created_at', True)
    column_formatters = {
        'url': _url_formatter,
        'final_url': _url_formatter,
        'method': lambda v, c, m, p: getattr(m, p).value,
        'created_at': date_formatter,
        'text': lambda v, c, m, p: Markup(
            '<pre><code class="language-html">{}</code></pre>'.format(
                Markup.escape(getattr(m, p))
            )
        ),
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
