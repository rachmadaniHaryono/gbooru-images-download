import json

from flask import flash
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView
from wtforms import fields, validators
import requests
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
        try:
            model = self.model()
            form.populate_obj(model)
            kwargs = {}
            if model.kwargs_json:
                kwargs = json.loads(form.kwargs_json)
            # TODO
            resp = requests.request(model.url_input, model.method, **kwargs)
            # resp to model
            model.status_code = resp.status_code
            model.final_url = resp.url  # TODO
            model.text = resp.text
            model.json = resp.json()
            model.link = resp.link
            model.reason = resp.reason
            # populate_obj finished
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
