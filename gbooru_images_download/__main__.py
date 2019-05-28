#!/usr/bin/env python3
"""Server module."""
from logging.handlers import TimedRotatingFileHandler
import logging
import os

from appdirs import user_data_dir
from flask import Flask
from flask.cli import FlaskGroup
from flask_admin import Admin
from flask_admin._compat import text_type
from flask_admin.contrib.sqla import fields
from flask_migrate import Migrate
from sqlalchemy.orm.util import identity_key
import click

from gbooru_images_download import models, views


APP_DATA_DIR = user_data_dir('gbooru_images_download', 'rachmadaniharyono')


def create_app(db_uri="sqlite:///:memory:"):
    """create app."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app and db
    models.db.init_app(app)
    app.app_context().push()
    models.db.create_all()

    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': models.db, 'models': models, 'session': models.db.session}

    Migrate(app, models.db)
    # flask-admin
    category_manage = 'Manage'
    app_admin = Admin(
        app, name='Gbooru images download', template_mode='bootstrap3',
        index_view=views.HomeView(name='Home', template='gbooru_images_download/index.html', url='/'))  # NOQA
    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """This is a script for gbooru-images-download application."""
    pass


if __name__ == '__main__':
    cli()
