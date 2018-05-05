"""Forms module."""
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional
from yapsy.PluginManager import PluginManager


from gbooru_images_download import models, plugin, api


def get_parser_choices():
    manager = PluginManager(plugin_info_ext='ini')
    manager.setCategoriesFilter({
        "parser": api.ParserPlugin,
    })
    manager.setPluginInfoExtension('ini')
    manager.setPluginPlaces([plugin.__path__[0]])
    manager.collectPlugins()
    plugins = manager.getAllPlugins()
    res = [('all', 'all: get images from all parser'), ]
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
