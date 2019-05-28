import os
import tempfile

import pytest


from gbooru_images_download.__main__ import create_app
from gbooru_images_download import models


@pytest.fixture
def client():
    app = create_app()
    db_fd, db_path = tempfile.mkstemp()
    db_uri = 'sqlite:///' + db_path
    # to use memory
    # db_uri = 'sqlite://'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        models.db.init_app(app)
        models.db.create_all()

    yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/')
    assert rv.status_code == 200
