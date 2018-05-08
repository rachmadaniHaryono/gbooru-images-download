#!/usr/bin/python3
from urllib.parse import urlparse, urlencode, parse_qs, urljoin, quote_plus
import hashlib
import json
import os
import shutil
import tempfile

from bs4 import BeautifulSoup
from PIL import Image
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
import requests
import structlog
try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    SELENIUM_ENABLED = True
except ImportError:
    SELENIUM_ENABLED = False

import gbooru_images_download as gid
from . import models, exceptions, plugin

log = structlog.getLogger(__name__)


def sha256_checksum(filename, block_size=65536):
    """sha256 checksum."""
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as file_path:
        for block in iter(lambda: file_path.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


def get_plugin_manager():
    manager = PluginManager(plugin_info_ext='ini')
    manager.setCategoriesFilter({
        "parser": ParserPlugin,
        'tag_preprocessor': TagPreProcessor,
    })
    manager.setPluginPlaces([plugin.__path__[0]])
    manager.collectPlugins()
    return manager


def get_json_response(query, page=1):
    url_page = page - 1
    url_query = {
        'q': query, 'ijn': str(url_page), 'start': str(int(url_page) * 100),
        'asearch': 'ichunk', 'async': '_id:rg_s,_pms:s', 'tbm': 'isch',
    }
    parsed_url = urlparse('https://www.google.com/search')
    query_url = parsed_url._replace(query=urlencode(url_query)).geturl()
    log.debug('query url', url=query_url)
    resp = requests.get(query_url)
    return resp.json()


def get_data(html_tag):
    """get data."""
    res = {}
    imgres_url = html_tag.select_one('a').get('href', None)
    imgref_url = parse_qs(urlparse(imgres_url).query).get('imgrefurl', [None])[0]
    res['tag'] = []
    res['tag'].append(('imgres url', imgres_url))
    res['tag'].append(('imgref url', imgref_url))
    # json data
    json_data = json.loads(html_tag.select_one('.rg_meta').text)
    res['json_data'] = json_data
    for key, value in json_data.items():
        res['tag'].append((key, value))
    # image url
    imgres_url_query = parse_qs(urlparse(imgres_url).query)
    if imgres_url_query:
        url_from_img_url = imgres_url_query.get('imgurl', [None])[0]
        img_url_width = int(imgres_url_query.get('w', [None])[0])
        img_url_height = int(imgres_url_query.get('h', [None])[0])
    else:
        url_from_img_url = json_data['ou']
        img_url_width = int(json_data['ow'])
        img_url_height = int(json_data['oh'])
    res['img_url'] = {
        'value': url_from_img_url,
        'width': img_url_width,
        'height': img_url_height
    }
    # thumbnail url
    res['thumbnail_url'] = {
        'value': json_data['tu'],
        'width': int(json_data['tw']),
        'height': int(json_data['th']),
    }
    return res


def get_or_create_image_url(dict_input, session=None):
    """Get or create match result from json response.

    Example dict_input:

        {'value': 'example.com/1.jpg', 'height': 100, 'width':100}
    """
    session = models.db.session if session is None else session
    m, created = models.get_or_create(session, models.Url, value=dict_input['value'])
    for item in ('width', 'height'):
        value = dict_input.get(item, None)
        if value:
            setattr(m, item, value)
    session.add(m)
    return m, created


def get_or_create_match_result(data, session=None):
    """Get match result."""
    session = models.db.session if session is None else session
    img_url = get_or_create_image_url(dict_input=data['img_url'], session=session)[0]
    thumbnail_url = get_or_create_image_url(dict_input=data['thumbnail_url'], session=session)[0]
    model, created = models.get_or_create(
        session, models.MatchResult, img_url=img_url, thumbnail_url=thumbnail_url)
    json_data_m = models.get_or_create(
        session, models.JsonData, value=data['json_data'])[0]
    if json_data_m not in model.json_data:
        model.json_data.append(json_data_m)
    manager = get_plugin_manager()
    for plug in manager.getPluginsOfCategory('tag_preprocessor'):
        data['tag'] = list(plug.plugin_object.run_tag_preprocessor(data['tag']))
    for nm_val, tag_val in data['tag']:
        tag_kwargs = {'value': str(tag_val)}
        if nm_val:
            namespace = models.get_or_create(session, models.Namespace, value=nm_val)[0]
            tag_kwargs['namespace'] = namespace
        tag = models.get_or_create(session, models.Tag, **tag_kwargs)[0]
        model.img_url.tags.append(tag)
    session.add(model)
    return model, created


def get_match_results(json_response=None, session=None):
    """Get match results."""
    session = models.db.session if session is None else session
    if json_response is not None:
        html = json_response[1][1]
        soup = BeautifulSoup(html, 'html.parser')
        for html_tag in soup.select('.rg_bx'):
            data = get_data(html_tag=html_tag)
            model = get_or_create_match_result(session=session, data=data)[0]
            session.add(model)
            yield model
    else:
        yield


def get_or_create_search_query(query, page=1, disable_cache=False, session=None):
    """Get or create search_query."""
    session = models.db.session if session is None else session
    mode = None
    search_term = models.get_or_create(session, models.SearchTerm, value=query)[0]
    with session.no_autoflush:
        model, created = models.get_or_create(
            session, models.SearchQuery, search_term=search_term, page=page)

    if created or disable_cache:
        manager = get_plugin_manager()
        if mode == 'all':
            pass
            # plugs = manager.getAllPlugins()
            # match_results = plugs
            # match_results = sum(match_results, [])
        else:
            plug = manager.activatePluginByName('Google image', 'parser')
            match_results = plug.get_match_results(search_term, page=page, session=session)
        # json_resp = get_json_response(query=query, page=page)
        # match_results = list(get_match_results(json_response=json_resp, session=session))
        namespace = models.get_or_create(session, models.Namespace, value='query')[0]
        query_tag = models.get_or_create(session, models.Tag, namespace=namespace, value=query)[0]
        [x.img_url.tags.append(query_tag) for x in match_results if hasattr(x, 'img_url')]
        model.match_results.extend(match_results)
    session.add(model)
    return model, created


def add_tags_to_image_url(img_url, tags, session=None):
    """add tags to image url."""
    session = models.db.session if session is None else session
    tags_models = []
    for tag in tags:
        name = tag['value']
        namespace = tag['namespace']
        if not name:
            log.warning('tag only contain namespace', namespace=namespace)
            continue
        namespace_m = models.get_or_create(session, models.Namespace, value=namespace)[0]
        tag_m_kwargs = dict(value=name, namespace_id=namespace_m.id)
        tag_m = models.get_or_create(session, models.Tag, **tag_m_kwargs)[0]
        if tag_m not in img_url.tags:
            img_url.tags.append(tag_m)
        tags_models.append(tag_m)
        session.add(namespace_m)
        session.add(tag_m)
    session.add(img_url)
    return tags_models


def get_html_text(search_url):
    """Get HTML text from search url.

    Args:
        search_url: search url
    Returns:
        html text

    """
    def get_html_text_with_selenium(url):
        options = Options()
        options.add_argument("--headless")
        wd = webdriver.Firefox(firefox_options=options)
        new_su = parse_qs(urlparse(url).query).get('continue', [None])[0]
        if not new_su:
            raise ValueError('Unknown format: {}'.format(url))
        else:
            search_url_res = new_su
        wd.get(search_url_res)
        html_text = wd.page_source
        wd.close()
        log.debug('webdriver closed')
        return html_text, search_url_res

    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'  # NOQA
    headers = {'User-Agent': user_agent}
    parsed_su = urlparse(search_url)
    # su = search_url
    su_redirected = (parsed_su.netloc, parsed_su.path) == ('ipv4.google.com', '/sorry/index')

    if su_redirected and SELENIUM_ENABLED:
        log.debug('Use selenium')
        html_text, search_url = get_html_text_with_selenium(url=search_url)
    elif search_url:
        resp = requests.get(search_url, headers=headers, timeout=10)
        parsed_su = urlparse(resp.url)
        su_redirected = (parsed_su.netloc, parsed_su.path) == ('ipv4.google.com', '/sorry/index')
        html_text = resp.text
        keyword_text = 'Our systems have detected unusual traffic from your computer network.'
        if keyword_text in html_text and su_redirected and SELENIUM_ENABLED:
            html_text, search_url = get_html_text_with_selenium(url=resp.url)
        elif keyword_text in html_text:
            raise ValueError('Unusual traffic detected')
    else:
        raise ValueError('Unknown condition, search url: {}'.format(search_url))
    return html_text


def get_search_url(file_path=None, img_url=None):
    if not((file_path or img_url) and not (file_path and img_url)):
        raise ValueError('image url or file path only')
    if file_path:
        search_url = 'http://www.google.com/searchbyimage/upload'
        multipart = {'encoded_image': (file_path, open(file_path, 'rb')), 'image_content': ''}
        response = requests.post(search_url, files=multipart, allow_redirects=False)
        return response.headers['Location']
    elif img_url:
        url_templ = 'https://www.google.com/searchbyimage?image_url={}&safe=off'
        search_url_from_image = url_templ.format(quote_plus(img_url))
        user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'  # NOQA
        headers = {'User-Agent': user_agent}
        resp = requests.get(search_url_from_image, headers=headers, timeout=10)
        return resp.url
    else:
        raise ValueError('Unknown condition, file path:{} url:{}'.format(file_path, img_url))


def parse_img_search_html(html):
    """parse image search html."""
    base_url = 'https://www.google.com'
    search_page = html
    kwargs = {}
    # parsing: size_search_url
    size_search_tag = search_page.select_one('._v6 .gl a')
    if not size_search_tag:
        size_search_tag = search_page.select_one('.card-section span > a[href^="/search"]')
    if size_search_tag:
        size_search_url = size_search_tag.attrs.get('href', None)
        if size_search_url:
            kwargs['size_search_url'] = urljoin(base_url, size_search_url)
    # parsing: similar search url
    similar_search_tag = search_page.select_one('h3._DM a')
    if not similar_search_tag:
        similar_search_tag = search_page.select_one('h3 a[href^="/search"]')
    if similar_search_tag:
        similar_search_url = similar_search_tag.attrs.get('href', None)
        if similar_search_url:
            kwargs['similar_search_url'] = urljoin(base_url, similar_search_url)
    # parsing: image guess
    image_guess_tag = search_page.select_one('._hUb a')
    if not image_guess_tag:
        image_guess_tag = search_page.select_one('.card-section > div > a')
    if image_guess_tag:
        kwargs['img_guess'] = image_guess_tag.text
    # parsing: main similar result
    main_similar_tags = search_page.select('.rg_ul .rg_el')
    msr_models = []
    if main_similar_tags:
        for tag in main_similar_tags:
            item = {}
            item['search_url'] = tag.select_one('a').attrs.get('href', None)
            item['search_url'] = urljoin(base_url, item['search_url'])
            img_tag = tag.select_one('img')
            item['title'] = img_tag.attrs.get('title', None)
            msr_models.append(item)
    kwargs['MainSimilarResult'] = msr_models
    # parsing: text match parsing
    text_match_tags = search_page.select('._NId > .srg > .g')
    if not text_match_tags:
        text_match_tags = search_page.select('.srg > .g')
    tm_models = []
    if text_match_tags:
        for tag in text_match_tags:
            item = parse_text_match(tag, base_url=base_url)
            tm_models.append(item)
    kwargs['TextMatch'] = tm_models
    return kwargs


def get_or_create_search_image(file_path=None, url=None, search_url=None, **kwargs):
    """get match result from file.

    Args:
        file_path: path to image file
        url: image url
        **disable_cache: disable cache
        **session: database session
        **thumb_folder: thumbnail folder
        **base_url: base url for google url
    """
    # kwargs
    disable_cache = kwargs.get('disable_cache', False)
    session = kwargs.get('session', None)
    base_url = kwargs.get('base_url', None)

    base_url = 'https://www.google.com' if base_url is None else base_url
    session = models.db.session if session is None else session
    if not((file_path or url) and not (file_path and url)):
        raise ValueError('input url or file path only')
    html_text = None
    if file_path:
        checksum = sha256_checksum(file_path)
        model = models.SearchImage.query.filter_by(img_checksum=checksum).first()
        created = True if not model else False
    elif url:
        img_url_m = models.ImageUrl.query.filter_by(url=url).first()
        model, created = None, False
        if img_url_m:
            model = models.SearchImage.query.filter_by(img_url=img_url_m).first()
        if not model:
            search_url = get_search_url(img_url=url)
            model, created = models.get_or_create(
                session, models.SearchImage, search_url=search_url)
            if not img_url_m:
                img_url_m = models.get_or_create(session, models.ImageUrl, url=url)[0]
            model.img_url = img_url_m
            model.search_url = search_url
        else:
            search_url = model.search_url
            created = True
    elif search_url:
        model, created = models.get_or_create(session, models.SearchImage, search_url=search_url)
    else:
        raise ValueError('Unknown condition, file path:{} url:{}'.format(file_path, url))
    if created or disable_cache:
        if file_path:
            search_url = get_search_url(file_path=file_path)
            if model is None:
                model = models.get_or_create(session, models.SearchImage, search_url=search_url)[0]
            model.img_checksum = checksum
        if search_url and not html_text:
            html_text = get_html_text(search_url=search_url)
        elif not search_url:
            raise ValueError('No search url found.')
        parsed_su = urlparse(search_url)
        if (parsed_su.netloc, parsed_su.path) == ('ipv4.google.com', '/sorry/index'):
            search_url = parse_qs(parsed_su.query).get('continue', [None])[0]
            if not search_url:
                raise ValueError('Unknown format: {}'.format(search_url))
        model.search_url = search_url
        # parsing
        search_page = BeautifulSoup(html_text, 'lxml')
        data = parse_img_search_html(search_page)
        msr_kwargs = data.pop('MainSimilarResult')
        tm_kwargs = data.pop('TextMatch')
        for key in data:
            setattr(model, key, data[key])
        for item in msr_kwargs:
            item_m = models.get_or_create(session, models.MainSimilarResult, **item)[0]
            model.main_similar_results.append(item_m)
        for item in tm_kwargs:
            img_url = item.pop('img_url', None)
            thumbnail_url = item.pop('thumbnail_url', None)
            tags = item.pop('img_url_tags', [])
            item_m = models.get_or_create(session, models.TextMatch, **item)[0]
            if img_url and thumbnail_url:
                img_url_m = models.get_or_create(session, models.ImageUrl, **img_url)[0]
                tags.extend([
                    {'namespace': 'page url', 'value': item['url']},
                    {'namespace': 'title', 'value': item['title']},
                    {'namespace': 'page url text', 'value': item['url_text']}
                ])
                add_tags_to_image_url(img_url_m, tags=tags, session=session)
                thumbnail_url_m = models.get_or_create(session, models.ImageUrl, **thumbnail_url)[0]  # NOQA
                # text match img model
                item_m.img = models.get_or_create(
                    session, models.MatchResult, img_url=img_url_m, thumbnail_url=thumbnail_url_m)[0]  # NOQA
            model.text_matches.append(item_m)
    session.add(model)
    return model, created


def parse_text_match(html_tag, base_url=None):
    """Parse text match html tag."""
    base_url = 'https://www.google.com' if base_url is None else base_url
    kwargs = {}
    kwargs['title'] = html_tag.select_one('h3').text
    kwargs['url'] = html_tag.select_one('h3 a').attrs.get('href', None)
    kwargs['url_text'] = html_tag.select_one('.f cite').text
    kwargs['text'] = html_tag.select_one('.st').text
    img_tag = html_tag.select_one('img')
    if img_tag:
        a_tag = img_tag.parent.parent
        imgres_url = urljoin(base_url, a_tag.get('href'))
        parsed_qs = parse_qs(urlparse(imgres_url).query)
        imgref_url = parsed_qs.get('imgrefurl', [None])[0]
        img_url_dict_input = {
            'url': parsed_qs.get('imgurl', [None])[0],
            'height': parsed_qs.get('h', [None])[0],
            'width': parsed_qs.get('w', [None])[0],
        }
        kwargs['img_url'] = img_url_dict_input
        thumbnail_url_dict_input = {
            'url': img_tag.attrs.get('src', None),
            'height': parsed_qs.get('tbnh', [None])[0],
            'width': parsed_qs.get('tbnw', [None])[0],
        }
        kwargs['thumbnail_url'] = thumbnail_url_dict_input
        img_url_tags = [
            {'namespace': 'imgres url', 'value': imgres_url},
        ]
        if imgref_url:
            img_url_tags.append({'namespace': 'page url', 'value': imgref_url})
            img_url_tags.append({'namespace': 'imgref url', 'value': imgref_url})
        kwargs['img_url_tags'] = img_url_tags
    return kwargs


def get_or_create_search_image_page(file_path=None, url=None, **kwargs):
    """Get or create page from search image.

    Args:
        file_path: path to image file
        url: image url
        **search_type: search type
        **page: page
        **disable_cache: disable cache
        **session: database session

    """
    # kwargs
    search_type = kwargs.get('search_type')
    page = kwargs.get('page', 1)
    disable_cache = kwargs.get('disable_cache', False)
    session = kwargs.get('session', None)

    # check input
    if page > 1:
        raise NotImplementedError('Only first page implemented yet.')
    if not((file_path or url) and not (file_path and url)):
        raise ValueError('input url or file_path only')

    session = models.db.session if session is None else session
    sm_model = get_or_create_search_image(file_path=file_path, url=url, disable_cache=disable_cache, session=session)[0]  # NOQA
    kwargs = {'search_img': sm_model, 'search_type': search_type, 'page': page}
    model, created = models.get_or_create(session, models.SearchImagePage, **kwargs)  # NOQA
    if created or disable_cache:
        gr_url = None
        if models.SearchImagePage.TYPE_SIMILAR == search_type:
            gr_url = sm_model.similar_search_url
        elif models.SearchImagePage.TYPE_SIZE == search_type:
            gr_url = sm_model.size_search_url
        else:
            log.error('Unknown search type: {}'.format(search_type))
        if not gr_url:
            session.add(sm_model)
            session.commit()
            raise exceptions.NoResultFound('No url found for search type: {}'.format(search_type))  # NOQA
        user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'  # NOQA
        resp = requests.get(gr_url, headers={'User-Agent': user_agent}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for html_tag in soup.select('.rg_bx'):
            data = get_data(html_tag)
            mr_model = get_or_create_match_result(session=session, data=data)[0]
            model.match_results.append(mr_model)
    session.add(model)
    return model, created


def get_or_create_image_file_with_thumbnail(file_path, **kwargs):
    """Get or create image file with thumbnail.

    Args:
        file_path: path to image file
        **disable_cache: disable cache
        **session: database session
        **thumb_folder: thumbnail folder
    """
    # kwargs
    disable_cache = kwargs.get('disable_cache', False)
    session = kwargs.get('session', None)
    thumb_folder = kwargs.get('thumb_folder', None)

    session = models.db.session if session is None else session
    thumb_folder = thumb_folder if thumb_folder else models.DEFAULT_THUMB_FOLDER
    img_file, img_file_created = \
        get_or_create_image_file(file_path, disable_cache=disable_cache, session=session)
    is_thumbnail_exist = False
    file_path_eq_thumb_path = False
    if img_file.thumbnail:
        thumbnail_path = os.path.join(thumb_folder, img_file.thumbnail.checksum + '.jpg')
        is_thumbnail_exist = os.path.isfile(thumbnail_path)
        file_path_eq_thumb_path = file_path == thumbnail_path
    if not is_thumbnail_exist and file_path_eq_thumb_path:
        img_file.thumbnail = img_file
    elif not is_thumbnail_exist:
        thumbnail_file = create_thumbnail(file_path, thumb_folder)
        log.debug('thumbnail created', m=thumbnail_file)
        thumbnail_file_model, _ = \
            get_or_create_image_file(thumbnail_file, disable_cache=disable_cache, session=session)
        thumbnail_file_model.thumbnail = thumbnail_file_model
        img_file.thumbnail = thumbnail_file_model
    return img_file, img_file_created


def get_or_create_image_file(file_path, disable_cache=False, session=None):
    """Get image file."""
    session = models.db.session if session is None else session
    checksum = sha256_checksum(file_path)
    model, created = models.get_or_create(
        session, models.ImageFile, checksum=checksum)
    if created or disable_cache:
        kwargs = {}
        img = Image.open(file_path)
        kwargs['width'] = img.size[0]
        kwargs['height'] = img.size[1]
        kwargs['img_format'] = img.format
        kwargs['size'] = os.path.getsize(file_path)
        for key, value in kwargs.items():
            setattr(model, key, value)
    return model, created


def create_thumbnail(file_path, thumbnail_folder):
    with tempfile.NamedTemporaryFile() as temp:
        img = Image.open(file_path)
        size = (256, 256)
        img.thumbnail(size)
        try:
            img.save(temp.name, 'JPEG')
        except OSError as err:
            log.warning('Error create thumbnail, convert to jpg first', error=err)
            img.convert('RGB').save(temp.name, 'JPEG')
        thumb_checksum = gid.sha256.sha256_checksum(temp.name)
        thumbnail_path = os.path.join(thumbnail_folder, thumb_checksum + '.jpg')
        if not os.path.isfile(thumbnail_path):
            shutil.copyfile(temp.name, thumbnail_path)
        return thumbnail_path


class ParserPlugin(IPlugin):
    """Base class for parser plugin."""

    def get_match_results(self, search_term, page=1, session=None, **kwargs):
        """main function used for plugin."""
        pass


class TagPreProcessor(IPlugin):
    """Base class for parser plugin."""

    def run_tag_preprocessor(self, tags):
        pass
