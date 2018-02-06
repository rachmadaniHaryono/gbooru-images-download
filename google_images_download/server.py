"""Server module."""
from logging.handlers import TimedRotatingFileHandler
from pprint import pprint
import logging
import os
import shutil
import tempfile

from appdirs import user_data_dir
from flask import Flask, request, flash, send_from_directory
from flask.cli import FlaskGroup
from flask_admin import Admin, BaseView, expose
import click
import structlog

from google_images_download import models, admin, api, sha256
from google_images_download.forms import FindImageForm


log = structlog.getLogger(__name__)


class ImageURLSingleView(BaseView):
    @expose('/')
    def index(self):
        """View for single image url."""
        kwargs = {}
        kwargs['search_url'] = request.args.get('u', None)
        kwargs['entry'] = models.ImageURL.query.filter_by(url=kwargs['search_url']).one_or_none()
        return self.render('google_images_download/image_url_view.html', **kwargs)


class FromFileSearchImageView(BaseView):
    @expose('/')
    def index(self):
        form = FindImageForm(request.args)
        file_path = form.file_path.data
        url = form.url.data
        search_type = form.search_type.data
        disable_cache = form.disable_cache.data
        render_template_kwargs = {'entry': None, 'form': form}
        file_exist = os.path.isfile(file_path) if file_path is not None else False
        empty_response = self.render(
            'google_images_download/from_file_search_page.html', **render_template_kwargs)
        raise_exception_ = True

        def get_entry(kwargs, raise_exception=False):
            entry = None
            try:
                entry, created = api.get_or_create_page_search_image(**kwargs)
                if created or disable_cache:
                    models.db.session.add(entry)
                    models.db.session.commit()
            except Exception as err:
                if raise_exception:
                    raise err
                msg = '{} raised:{}'.format(type(err), err)
                flash(msg, 'danger')
                log.debug(msg)
            return entry

        if not file_path and not url:
            return empty_response
        if url:
            kwargs = {'url': url, 'search_type': search_type, 'disable_cache': disable_cache}
            entry = get_entry(kwargs, raise_exception_)
            if not entry:
                return empty_response
        elif not file_path or not file_exist:
            if not file_exist:
                msg = 'File not exist: {}'.format(file_path)
                log.debug(msg)
                flash(msg, 'danger')
            return empty_response
        else:
            with tempfile.NamedTemporaryFile() as temp:
                shutil.copyfile(file_path, temp.name)
                kwargs = {
                    'file_path': temp.name,
                    'search_type': search_type,
                    'disable_cache': disable_cache
                }
                entry = get_entry(kwargs, raise_exception_)
                if not entry:
                    return empty_response
        log.debug('kwargs: %s', kwargs)
        log.debug('search type:%s match results:%s', search_type, len(entry.match_results))
        log.debug('URL:%s', request.url)
        render_template_kwargs['entry'] = entry
        return self.render(
            'google_images_download/from_file_search_page.html', **render_template_kwargs)


def create_app(script_info=None):
    """create app."""
    app = Flask(__name__)
    # logging
    directory = 'log'
    if not os.path.exists(directory):
        os.makedirs(directory)
    default_log_file = os.path.join(directory, 'google_images_download_server.log')
    file_handler = TimedRotatingFileHandler(default_log_file, 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)
    # reloader
    reloader = app.config['TEMPLATES_AUTO_RELOAD'] = bool(os.getenv('REDDITDL_RELOADER')) or app.config['TEMPLATES_AUTO_RELOAD']  # NOQA
    if reloader:
        app.jinja_env.auto_reload = True
    # app config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('GID_SQLALCHEMY_DATABASE_URI') or 'sqlite:///gid_debug.db'  # NOQA
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('GID_SERVER_SECRET_KEY') or os.urandom(24)
    app.config['WTF_CSRF_ENABLED'] = False
    # debug
    debug = app.config['DEBUG'] = bool(os.getenv('GID_DEBUG')) or app.config['DEBUG']
    if debug:
        app.config['DEBUG'] = True
        app.config['LOGGER_HANDLER_POLICY'] = 'debug'
        logging.basicConfig(level=logging.DEBUG)
        pprint.pprint(app.config)
    # app and db
    models.db.init_app(app)
    app.app_context().push()
    models.db.create_all()

    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': models.db}

    # flask-admin
    app_admin = Admin(
        app, name='Google images download', template_mode='bootstrap3',
        index_view=admin.HomeView(name='Home', template='google_images_download/index.html', url='/'))  # NOQA
    app_admin.add_view(FromFileSearchImageView(name='Image Search', endpoint='f'))
    app_admin.add_view(ImageURLSingleView(name='Image Viewer', endpoint='u'))
    app_admin.add_view(admin.SearchQueryView(models.SearchQuery, models.db.session, category='History'))  # NOQA
    app_admin.add_view(admin.MatchResultView(models.MatchResult, models.db.session, category='History'))  # NOQA
    app_admin.add_view(admin.JSONDataView(models.JSONData, models.db.session, category='History'))
    app_admin.add_view(admin.ImageURLView(models.ImageURL, models.db.session, category='History'))
    app_admin.add_view(admin.TagView(models.Tag, models.db.session, category='History'))
    app_admin.add_view(admin.ImageFileView(models.ImageFile, models.db.session, category='History'))  # NOQA
    app_admin.add_view(admin.SearchImageView(models.SearchImage, models.db.session, category='History'))  # NOQA
    # app_admin.add_view(admin.SearchImagePageView(models.SearchImagePage, models.db.session, category='History'))  # NOQA
    app_admin.add_view(admin.TextMatchView(models.TextMatch, models.db.session, category='History'))  # NOQA
    app_admin.add_view(admin.MainSimilarResultView(models.MainSimilarResult, models.db.session, category='History'))  # NOQA

    # routing
    app.add_url_rule('/t/<path:filename>', 'thumbnail', lambda x:send_from_directory(models.DEFAULT_THUMB_FOLDER, x))  # NOQA

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """This is a management script for application."""
    pass


@cli.command()
def check_thumbnails():
    """Check thumbnails."""
    create_app()
    # get all thumbnail files and checksum
    def_thumb_folder = os.path.join(user_data_dir('google_images_download', 'hardikvasa'), 'thumb')  # NOQA
    thumb_folder = def_thumb_folder
    listdir_res = [
        {'basename': x, 'path': os.path.join(thumb_folder, x)}
        for x in os.listdir(def_thumb_folder)
        if os.path.isfile(os.path.join(thumb_folder, x))
    ]
    filtered_ff = []
    for item in listdir_res:
        old_checksum = os.path.splitext(item['basename'])[0]
        checksum = sha256.sha256_checksum(os.path.join(thumb_folder, item['basename']))
        new_basename = checksum + '.jpg'
        new_path = os.path.join(thumb_folder, new_basename)
        if checksum != old_checksum:
            # move thumbnail
            shutil.move(item['path'], new_path)
            log.info('Move thumbnail', src=old_checksum, dst=checksum)
        filtered_ff.append({'basename': new_basename, 'path': new_path, 'checksum': checksum})

    new_model_sets = [api.get_or_create_image_file_with_thumbnail(x['path']) for x in filtered_ff]
    models.db.session.add_all([x[0] for x in new_model_sets])
    models.db.session.commit()


if __name__ == '__main__':
    cli()
