"""Forms module."""
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Optional
import wtforms

from gbooru_images_download import models


def get_parser_choices():
    manager = models.get_plugin_manager()
    plugins = manager.getPluginsOfCategory('mode')
    res = []
    for pg in plugins:
        res.append((pg.name, '{0.name}: {0.description}'.format(pg)))
    return res


class FindImageForm(FlaskForm):
    """Form for getting result from file search."""
    file_path = wtforms.StringField('File Path', validators=[Optional()])
    url = wtforms.StringField('URL', validators=[Optional()])
    search_type = wtforms.SelectField('Search Type', validators=[Optional()], choices=models.SearchImagePage.TYPES)  # NOQA
    disable_cache = wtforms.BooleanField(validators=[Optional()])


class IndexForm(FlaskForm):  # pylint: disable=too-few-public-methods
    """Form for index."""
    search_term = wtforms.StringField('search term', validators=[DataRequired()])
    mode = wtforms.SelectField('mode', choices=get_parser_choices())
    page = wtforms.IntegerField('page', default=1)
    disable_cache = wtforms.BooleanField(validators=[Optional()])


class ResponseParserForm(FlaskForm):
    response = wtforms.SelectField()
    parser = wtforms.SelectField()
