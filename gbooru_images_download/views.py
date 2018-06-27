import json

from flask_admin.contrib.sqla import ModelView
from wtforms import fields, validators
import structlog


log = structlog.getLogger(__name__)


class ResponseView(ModelView):
    can_edit = False
    can_view_details = False
    column_list = ('url', 'status_code')
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
        # RadioField can't be created on form_overrides
        # it need choices list to at init
        form.method = fields.RadioField(
            'Method', choices=[('head', ' head'), ('post', 'post'), ('get', 'get')])

        def json_check(form, field):
            if form.data:
                try:
                    json.loads(form.data)
                except Exception as e:
                    message = 'Json check failed: {}'.format(str(e))
                    raise validators.ValidationError(message)

        form.url_input = fields.StringField(
            'Url', [validators.required(), validators.URL(), json_check])
        return form

    def create_model(self, form):
        model = self.model.create(
            url=form.url_input.data, method=form.method.data, session=self.session,
            kwargs_json=form.kwargs_json.data,
            on_model_change_func=lambda x: self._on(form, x, True),
            handle_view_exception=self.handle_view_exception,
            after_model_change_func=lambda x: self.after(form, x, True)
        )
        return model
