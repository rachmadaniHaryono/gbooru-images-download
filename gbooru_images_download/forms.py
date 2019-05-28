"""Forms module."""
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Optional
import wtforms

from gbooru_images_download import models


class IndexForm(FlaskForm):  # pylint: disable=too-few-public-methods
    """Form for index."""
    search_term = wtforms.StringField('search term', validators=[DataRequired()])
    page = wtforms.IntegerField('page', default=1)
    disable_cache = wtforms.BooleanField(validators=[Optional()])


class ResponseParserForm(FlaskForm):
    response = wtforms.SelectField()
    parser = wtforms.SelectField()
