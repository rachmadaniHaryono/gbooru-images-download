"""Server module."""
from logging.handlers import TimedRotatingFileHandler
import logging
import os
import shutil
import tempfile

from appdirs import user_data_dir
from flask import Flask, request, flash, send_from_directory
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
import click
import structlog

from google_images_download import models, admin, api, sha256
from google_images_download.forms import FindImageForm


app = Flask(__name__)
log = structlog.getLogger(__name__)


class ImageURLSingleView(BaseView):
    @expose('/')
    def index(self):
        """View for single image url."""
        search_url = request.args.get('u', None)
        entry = models.ImageURL.query.filter_by(url=search_url).one_or_none()
        return self.render(
            'google_images_download/image_url_view.html', entry=entry, search_url=search_url)


@app.route('/t/<path:filename>')
def thumbnail(filename):
    """Thumbnail url."""
    return send_from_directory(models.DEFAULT_THUMB_FOLDER, filename)


def shell_context():
    """Return shell context."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    models.db.init_app(app)
    return {'app': app, 'db': models.db, 'models': models, }


def create_app(script_info=None):  # pylint: disable=unused-argument
    """Create app."""
    app.shell_context_processor(shell_context)
    if not app.debug:
        directory = 'log'
        if not os.path.exists(directory):
            os.makedirs(directory)
        default_log_file = os.path.join(directory, 'google_images_download_server.log')
        file_handler = TimedRotatingFileHandler(default_log_file, 'midnight')
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
        app.logger.addHandler(file_handler)

    app_admin = Admin(app, name='google image download', template_mode='bootstrap3')
    app_admin.add_view(ModelView(models.SearchQuery, models.db.session))
    app_admin.add_view(ModelView(models.MatchResult, models.db.session))
    app_admin.add_view(ModelView(models.ImageURL, models.db.session))
    return app


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
                app.logger.debug(msg)
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
                app.logger.debug(msg)
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
        app.logger.debug('kwargs: %s', kwargs)
        app.logger.debug('search type:%s match results:%s', search_type, len(entry.match_results))
        app.logger.debug('URL:%s', request.url)
        render_template_kwargs['entry'] = entry
        return self.render(
            'google_images_download/from_file_search_page.html', **render_template_kwargs)


@click.group()
def cli():
    """CLI command."""
    pass


@cli.command()
def check_thumbnails():
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
        filtered_ff.append(
            {'basename': new_basename, 'path': new_path, 'checksum': checksum})

    app.config['DEBUG'] = True
    app.config['LOGGER_HANDLER_POLICY'] = 'debug'
    app.config['SECRET_KEY'] = os.getenv('DDG_SERVER_SECRET_KEY') or \
        os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gid_debug.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    models.db.init_app(app)
    app.app_context().push()
    models.db.create_all()
    new_model_sets = [
        api.get_or_create_image_file_with_thumbnail(x['path']) for x in filtered_ff]
    models.db.session.add_all([x[0] for x in new_model_sets])
    models.db.session.commit()


@cli.command()
@click.option("-h", "--host", default="127.0.0.1", type=str)
@click.option("-p", "--port", default=5000, type=int)
@click.option("-d", "--debug", is_flag=True)
@click.option("-r", "--reloader", is_flag=True)
@click.option("-t", "--threaded", is_flag=True)
def run(host='127.0.0.1', port=5000, debug=False, reloader=False, threaded=False):
    """Run the application server."""
    if reloader:
        app.jinja_env.auto_reload = True
        app.config["TEMPLATES_AUTO_RELOAD"] = True

    # logging
    directory = 'log'
    if not os.path.exists(directory):
        os.makedirs(directory)
    default_log_file = os.path.join(directory, 'google_images_download_server.log')
    file_handler = TimedRotatingFileHandler(default_log_file, 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gid_debug.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if debug:
        app.config['DEBUG'] = True
        app.config['LOGGER_HANDLER_POLICY'] = 'debug'
        app.config['SECRET_KEY'] = os.getenv('DDG_SERVER_SECRET_KEY') or os.urandom(24)
        app.config['WTF_CSRF_ENABLED'] = False
        models.db.init_app(app)
        app.app_context().push()
        models.db.create_all()
        logging.basicConfig(level=logging.DEBUG)

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

    app.run(
        host=host, port=port,
        debug=debug, use_debugger=debug,
        use_reloader=reloader,
        threaded=threaded
    )


if __name__ == '__main__':
    cli()
