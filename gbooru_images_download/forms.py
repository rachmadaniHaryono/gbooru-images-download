"""Forms module."""
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional

from gbooru_images_download import models, api


def get_parser_choices():
    manager = api.get_plugin_manager()
    plugins = manager.getPluginsOfCategory('mode')
    res = []
    for pg in plugins:
        res.append((pg.name, '{0.name}: {0.description}'.format(pg)))
    return res


class IndexForm(FlaskForm):  # pylint: disable=too-few-public-methods
    """Form for index."""
    query = StringField('query', validators=[DataRequired()])
    mode = SelectField('mode', choices=get_parser_choices())
    disable_cache = BooleanField(validators=[Optional()])


class FindImageForm(FlaskForm):
    """Form for getting result from file search."""
    file_path = StringField('File Path', validators=[Optional()])
    url = StringField('URL', validators=[Optional()])
    search_type = SelectField('Search Type', validators=[Optional()], choices=models.SearchImagePage.TYPES)  # NOQA
    disable_cache = BooleanField(validators=[Optional()])


class ResponseParserForm(FlaskForm):
    response = SelectField()
    parser = SelectField()
