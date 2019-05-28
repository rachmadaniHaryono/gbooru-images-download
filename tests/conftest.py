"""Module contain shared fixture function."""
import logging

from flask import Flask
import pytest

from gbooru_images_download import models


log = logging.getLogger('__name__')
vcr_log = logging.getLogger("vcr")
vcr_log.setLevel(logging.INFO)
logging.basicConfig()


@pytest.fixture()
def tmp_db(tmpdir):
    """Get tmp db."""
    app = Flask(__name__)
    tmp_db_path = tmpdir.join('temp.db')
    log.debug('db path', v=tmp_db_path)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + tmp_db_path.strpath
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    models.db.init_app(app)
    app.app_context().push()
    models.db.create_all()
    return models.db
