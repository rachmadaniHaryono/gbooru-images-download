"""Test server."""
import logging
import os
import tempfile
import unittest

import pytest
import vcr

from gbooru_images_download import models
from gbooru_images_download.__main__ import create_app


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)  # pylint: disable=invalid-name
vcr_log = logging.getLogger("vcr")  # pylint: disable=invalid-name
vcr_log.setLevel(logging.INFO)


class ServerTestCase(unittest.TestCase):
    """Server test case."""

    def setUp(self):
        app = create_app()
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.testing = True
        self.client = app.test_client()
        # setting app config to suppres warning
        with app.app_context():
            self.client.application.config.setdefault('WTF_CSRF_ENABLED', False)
            models.db.init_app(self.client.application)
            models.db.create_all()
        self.app = app

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.app.config['DATABASE'])

    @pytest.mark.no_travis
    def test_index(self):
        """Test index."""
        retval = self.client.get('/')
        assert retval.status_code == 200
        assert retval.data.decode()


if __name__ == '__main__':
    unittest.main()
