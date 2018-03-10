"""Server module."""
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import unquote_plus
import pprint
import logging
import os
import shutil
import tempfile

from appdirs import user_data_dir
from flask import Flask, request, flash, send_from_directory, jsonify
from flask.cli import FlaskGroup
from flask.views import View
from flask_admin import Admin, BaseView, expose
from flask_admin._compat import text_type
from flask_admin.contrib.sqla import fields, ModelView
from sqlalchemy.orm.util import identity_key
import click
import structlog

from gbooru_images_download import models, admin, api, sha256
from gbooru_images_download.forms import FindImageForm


log = structlog.getLogger(__name__)


class ImageURLSingleView(BaseView):
    @expose('/')
    def index(self):
        """View for single image url."""
        kwargs = {}
        kwargs['search_url'] = request.args.get('u', None)
        kwargs['entry'] = models.ImageURL.query.filter_by(url=kwargs['search_url']).one_or_none()
        return self.render('gbooru_images_download/image_url_view.html', **kwargs)


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
        raise_exception_ = True

        def get_entry(kwargs, raise_exception=False):
            entry = None
            session = models.db.session
            if kwargs.get('session', None) is not None:
                session = kwargs['session']
            else:
                kwargs['session'] = session
            session = models.db.session if session is None else session
            try:
                entry, created = api.get_or_create_page_search_image(**kwargs)
                if created or disable_cache:
                    session.add(entry)
                    session.commit()
            except Exception as err:
                if raise_exception:
                    raise err
                msg = '{} raised:{}'.format(type(err), err)
                flash(msg, 'danger')
                log.debug(msg)
            return entry

        entry = None
        session = models.db.session
        kwargs = {'search_type': search_type, 'disable_cache': disable_cache, 'session': session}
        if not file_path and not url:
            pass
        elif url:
            kwargs['url'] = url
            entry = get_entry(kwargs, raise_exception_)
        elif file_path and not file_exist:
            msg = 'File not exist: {}'.format(file_path)
            log.debug(msg)
            flash(msg, 'danger')
        else:
            with tempfile.NamedTemporaryFile() as temp:
                shutil.copyfile(file_path, temp.name)
                kwargs['file_path'] = temp.name
                entry = get_entry(kwargs, raise_exception_)
        log.debug('kwargs: {}'.format(kwargs))
        log.debug('search type:{} match results:{}'.format(
            search_type,
            len(entry.match_results) if entry else 0)
        )
        log.debug('URL:{}'.format(request.url))
        render_template_kwargs['entry'] = entry
        return self.render('gbooru_images_download/from_file_search_page.html', **render_template_kwargs)  # NOQA


class ThreadJsonView(View):

    def dispatch_request(self, search_query=None, page=1):
        """Dispatch request.
        Return format:

        {'page title': <search_query>,
        'posts':[
            {'url': <>, 'query': [<search_query>, <>, ...], 'page url':[<>, ...],
            'subtitle':[<>, ...], 'title': [<>, ...], site: <>, 'site title': [<>, ...]},
            ...
        ]}
        """
        session = models.db.session
        disable_cache = False
        kwargs = dict(query=search_query, page=page, disable_cache=disable_cache, session=session)
        model, created = api.get_or_create_search_query(**kwargs)
        if created or disable_cache:
            session.add(model)
            session.commit()
        res = {
            'page title': search_query, 'posts': [],
            'source time': int(model.created_at.timestamp())}
        for match_result in model.match_results:
            post = {}
            post['url'] = match_result.img_url.url
            post['source time'] = int(match_result.created_at.timestamp())
            post['filename'] = unquote_plus(os.path.splitext(os.path.basename(post['url']))[0])
            post['query'] = [search_query]
            post['tags'] = []
            post['page url'] = [match_result.imgref_url] if match_result.imgref_url else []
            for tag in match_result.img_url.tags:
                if not tag.namespace:
                    post['tags'].append(tag.name)
                else:
                    post.setdefault(tag.namespace, []).append(tag.name)
                # backward compatibiliy
                if tag.namespace == 'image page url':
                    post.setdefault('page url', []).append(tag.name)
            for other_mr in match_result.img_url.match_results:
                if other_mr == match_result:
                    continue
                if other_mr.search_query:
                    post['query'].append(other_mr.search_query.search_query)
                if other_mr.imgref_url:
                    post['page url'].append(other_mr.imgref_url)
            # remove duplicate
            post['query'] = list(set(post['query']))
            post['page url'] = list(set(post['page url']))
            res['posts'].append(post)
        return jsonify(res)


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
    if not os.path.exists(models.APP_DATA_DIR):
        os.makedirs(models.APP_DATA_DIR)
    log_dir = os.path.join(models.APP_DATA_DIR, 'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    default_log_file = os.path.join(log_dir, 'gbooru_images_download_server.log')
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
        print('Log file: {}'.format(default_log_file))
    # app and db
    models.db.init_app(app)
    app.app_context().push()
    models.db.create_all()

    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': models.db}

    # flask-admin
    app_admin = Admin(
        app, name='Gbooru images download', template_mode='bootstrap3',
        index_view=admin.HomeView(name='Home', template='gbooru_images_download/index.html', url='/'))  # NOQA
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
    app_admin.add_view(admin.FilteredImageURLView(models.FilteredImageURL, models.db.session, category='Filter'))  # NOQA
    app_admin.add_view(ModelView(models.HiddenNamespace, models.db.session, category='Filter'))  # NOQA

    # routing
    app.add_url_rule('/t/<path:filename>', 'thumbnail', lambda filename:send_from_directory(models.DEFAULT_THUMB_FOLDER, filename))  # NOQA
    thread_json_view = ThreadJsonView.as_view("thread_json")
    app.add_url_rule('/tj/<path:search_query>', view_func=thread_json_view)
    app.add_url_rule('/tj/<path:search_query>/<int:page>', view_func=thread_json_view)
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
    def_thumb_folder = os.path.join(user_data_dir('gbooru_images_download', 'hardikvasa'), 'thumb')  # NOQA
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
