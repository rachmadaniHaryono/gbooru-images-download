#!/usr/bin/env python3
"""Server module."""
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import unquote_plus
import logging
import os
import shutil
import tempfile

from appdirs import user_data_dir
from flask import Flask, request, flash, jsonify
from flask.cli import FlaskGroup
from flask.views import View
from flask_admin import Admin, BaseView, expose
from flask_admin._compat import text_type
from flask_admin.contrib.sqla import fields
from flask_migrate import Migrate
from sqlalchemy.orm.util import identity_key
import click
import structlog
# api for later
# from flask_restful import Api, Resource
# from flasgger import Swagger

from gbooru_images_download import models, admin, api, views


log = structlog.getLogger(__name__)
APP_DATA_DIR = user_data_dir('gbooru_images_download', 'rachmadaniharyono')


def get_pk_from_identity(obj):
    """Monkey patck to fix flask-admin sqla error.

    https://github.com/flask-admin/flask-admin/issues/1588
    """
    res = identity_key(instance=obj)
    cls, key = res[0], res[1]  # NOQA
    return u':'.join(text_type(x) for x in key)


fields.get_pk_from_identity = get_pk_from_identity


def create_app(script_info=None):
    """create app."""
    app = Flask(__name__)
    # logging
    if not os.path.exists(APP_DATA_DIR):
        os.makedirs(APP_DATA_DIR)
    log_dir = os.path.join(APP_DATA_DIR, 'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    default_log_file = os.path.join(log_dir, 'gbooru_images_download_server.log')
    file_handler = TimedRotatingFileHandler(default_log_file, 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)
    # reloader
    reloader = app.config['TEMPLATES_AUTO_RELOAD'] = bool(os.getenv('GID_RELOADER')) or app.config['TEMPLATES_AUTO_RELOAD']  # NOQA
    if reloader:
        app.jinja_env.auto_reload = True
    # app config
    database_path = 'gid_debug.db'
    database_uri = 'sqlite:///' + database_path
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        os.getenv('GID_SQLALCHEMY_DATABASE_URI') or database_uri # NOQA
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('GID_SERVER_SECRET_KEY') or os.urandom(24)
    app.config['WTF_CSRF_ENABLED'] = False
    print('Log file: {}'.format(default_log_file))
    print('DB uri: {}'.format(app.config['SQLALCHEMY_DATABASE_URI']))
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
    app_admin.add_view(views.SearchQueryView(models.SearchQuery, models.db.session, category=category_manage))  # NOQA
    app_admin.add_view(views.MatchResultView(models.MatchResult, models.db.session, category=category_manage))  # NOQA
    app_admin.add_view(views.UrlView(models.Url, models.db.session, category=category_manage))
    app_admin.add_view(views.NetlocView(models.Netloc, models.db.session, category=category_manage))  # NOQA
    app_admin.add_view(views.NamespaceView(models.Namespace, models.db.session, category=category_manage))  # NOQA
    app_admin.add_view(admin.TagView(models.Tag, models.db.session, category=category_manage))
    app_admin.add_view(views.ResponseView(models.Response, models.db.session, category=category_manage))  # NOQA
    app_admin.add_view(views.PluginView(models.Plugin, models.db.session))
    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """This is a script for gbooru-images-download application."""
    pass


if __name__ == '__main__':
    cli()
