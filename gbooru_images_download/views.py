from flask_admin.contrib.sqla import ModelView
from flask_admin import expose
from wtforms import fields


class ResponseView(ModelView):
    can_edit = False
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
        form.url_input = fields.StringField('Url')
        return form
