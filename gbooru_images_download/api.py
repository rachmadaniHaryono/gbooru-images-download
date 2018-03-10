#!/usr/bin/python3
from urllib.parse import urlparse, urlencode, parse_qs, urljoin, quote_plus
import shutil
import hashlib
import json
import tempfile
import os

from bs4 import BeautifulSoup
from PIL import Image
import requests
import structlog
try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    SELENIUM_ENABLED = True
except ImportError:
    SELENIUM_ENABLED = False

import gbooru_images_download as gid

log = structlog.getLogger(__name__)


def sha256_checksum(filename, block_size=65536):
    """sha256 checksum."""
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as file_path:
        for block in iter(lambda: file_path.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


def get_or_create_search_query(query, page=1, disable_cache=False, session=None):
    """Get or create search_query."""
    session = gid.models.db.session if session is None else session
    url_page = page - 1
    url_query = {
        'q': query, 'tbm': 'isch', 'ijn': str(url_page),
        'start': str(int(url_page) * 100),
        'asearch': 'ichunk', 'async': '_id:rg_s,_pms:s'
    }
    parsed_url = urlparse('https://www.google.com/search')
    query_url = parsed_url._replace(query=urlencode(url_query)).geturl()
    kwargs = {'search_query': query, 'page': page}
    model, created = gid.models.get_or_create(session, gid.models.SearchQuery, **kwargs)
    debug_kwargs = \
        dict(search_query_id=model.id, page=page, created=created, cache_disabled=disable_cache)
    log.debug('SearchQuery', **debug_kwargs)
    if created or disable_cache:
        log.debug('query url', url=query_url)
        resp = requests.get(query_url)
        json_resp = resp.json()
        match_result_ms = []
        match_result_sets = get_or_create_match_result_from_json_resp(
            json_resp, search_query=model, session=session)
        for match_result_m, match_result_m_created in match_result_sets:
            match_result_ms.append(match_result_m)
        model.match_results.extend(match_result_ms)
    return model, created


def parse_match_result_html_tag(html_tag):
    """Get or create match result from json response"""
    kwargs = {}
    imgres_url = html_tag.select_one('a').get('href', None)
    imgref_url = parse_qs(urlparse(imgres_url).query).get('imgrefurl', [None])[0]

    # json data
    json_data = json.loads(html_tag.select_one('.rg_meta').text)
    if 'msu' in json_data and json_data['msu'] != json_data['si']:
        log.warning("msu-value different with si-value", msu=json_data['msu'], si=json_data['si'])
    kwargs['json_data'] = json_data

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
    kwargs['img_url'] = {
        'url': url_from_img_url,
        'width': img_url_width,
        'height': img_url_height
    }

    # add tags to image url
    img_url_tags = [
        {'namespace': 'picture title', 'name': json_data['pt']},
        {'namespace': 'site', 'name': json_data['isu']},
        {'namespace': 'imgres url', 'name': imgres_url},
    ]
    if imgref_url:
        img_url_tags.append({'namespace': 'page url', 'name': imgref_url})
        img_url_tags.append({'namespace': 'imgref url', 'name': imgref_url})
    if 'st' in json_data:
        img_url_tags.append({'namespace': 'site title', 'name': json_data['st']})
    if 'ru' in json_data:
        img_url_tags.append({'namespace': 'image page url', 'name': json_data['ru']})
    picture_subtitle = json_data.get('s', None)
    if picture_subtitle:
        img_url_tags.append({'namespace': 'picture subtitle', 'name': picture_subtitle})
    img_ext = json_data.get('ity', None)
    if img_ext:
        img_url_tags.append({'namespace': 'img ext', 'name': img_ext})
    kwargs['img_url_tags'] = img_url_tags

    # thumbnail url
    kwargs['thumbnail_url'] = {
        'url': json_data['tu'],
        'width': int(json_data['tw']),
        'height': int(json_data['th']),
    }
    return kwargs


def get_or_create_image_url_from_dict(dict_input, session=None):
    """Get or create match result from json response.

    Example dict_input:

        {'url': 'example.com/1.jpg', 'height': 100, 'width':100}
    """
    session = gid.models.db.session if session is None else session
    m, created = gid.models.get_or_create(
        session, gid.models.ImageURL, url=dict_input['url'])
    if dict_input['width']:
        m.width = dict_input['width']
    if dict_input['height']:
        m.height = dict_input['height']
    session.add(m)
    return m, created


def get_or_create_match_result_from_html_soup(html_tag, search_query=None, session=None):
    """Get or create match result from html_soup"""
    session = gid.models.db.session if session is None else session
    kwargs = parse_match_result_html_tag(html_tag)
    kwargs['json_data'] = json_data = \
        gid.models.get_or_create(session, gid.models.JSONData, value=kwargs['json_data'])[0]
    kwargs['json_data_id'] = json_data.id
    # image url
    kwargs['img_url'] = img_url = \
        get_or_create_image_url_from_dict(kwargs['img_url'], session=session)[0]
    kwargs['thumbnail_url'] = thumbnail_url = \
        get_or_create_image_url_from_dict(kwargs['thumbnail_url'], session=session)[0]
    add_tags_to_image_url(img_url, kwargs.pop('img_url_tags', []), session=session)

    # id
    kwargs['img_url_id'] = img_url.id
    kwargs['thumbnail_url_id'] = thumbnail_url.id
    # optional search_query
    if search_query:
        kwargs['search_query'] = search_query
    if not search_query:
        model, created = gid.models.get_or_create(session, gid.models.MatchResult, **kwargs)
    else:
        new_kwargs = {
            'search_query': search_query,
            'img_url': img_url,
            'thumbnail_url': thumbnail_url,
        }
        model, created = gid.models.get_or_create(session, gid.models.MatchResult, **new_kwargs)
        for key, value in kwargs.items():
            setattr(model, key, value)
    return model, created


def get_or_create_match_result_from_json_resp(json_resp, search_query=None, session=None):
    """Get or create match result from json response"""
    session = gid.models.db.session if session is None else session
    html = json_resp[1][1]
    soup = BeautifulSoup(html, 'html.parser')
    for html_tag in soup.select('.rg_bx'):
        model, create = \
            get_or_create_match_result_from_html_soup(html_tag, search_query, session=session)
        yield model, create


def add_tags_to_image_url(img_url, tags, session=None):
    """add tags to image url."""
    session = gid.models.db.session if session is None else session
    models = gid.models
    tags_models = []
    for tag in tags:
        name = tag['name']
        namespace = tag['namespace']
        if not name:
            log.warning('tag only contain namespace', namespace=namespace)
            continue
        namespace_m = gid.models.get_or_create(session, models.Namespace, value=namespace)[0]
        tag_m_kwargs = dict(name=name, namespace_id=namespace_m.id)
        tag_m = gid.models.get_or_create(session, models.Tag, **tag_m_kwargs)[0]
        if tag_m not in img_url.tags:
            img_url.tags.append(tag_m)
        tags_models.append(tag_m)
        session.add(namespace_m)
        session.add(tag_m)
    session.add(img_url)
    return tags_models


def get_html_text_from_search_url(search_url=None, img_url=None):
    """Get HTML text from search url"""
    if not((search_url or img_url) and not (search_url and img_url)):
        raise ValueError('search url or image url only')

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
    if not search_url and img_url:
        url_templ = 'https://www.google.com/searchbyimage?image_url={}&safe=off'
        search_url_from_image = url_templ.format(quote_plus(img_url))
        resp = requests.get(search_url_from_image, headers=headers, timeout=10)
        search_url = resp.url
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
        raise ValueError('Unknown condition, search url: {} url: {}'.format(search_url, img_url))
    return {'html_text': html_text, 'search_url': search_url}


def get_search_url_from_img(file_path):
        search_url = 'http://www.google.com/searchbyimage/upload'
        multipart = {'encoded_image': (file_path, open(file_path, 'rb')), 'image_content': ''}
        response = requests.post(search_url, files=multipart, allow_redirects=False)
        return response.headers['Location']


def parse_img_search_html(html, base_url=None):
    """parse image search html."""
    search_page = html
    kwargs = {}
    base_url = base_url if base_url is not None else 'https://www.google.com'
    # parsing: size_search_url
    size_search_tag = search_page.select_one('._v6 .gl a')
    if size_search_tag:
        size_search_url = size_search_tag.attrs.get('href', None)
        if size_search_url:
            kwargs['size_search_url'] = urljoin(base_url, size_search_url)
    # parsing: similar search url
    similar_search_tag = search_page.select_one('h3._DM a')
    if similar_search_tag:
        similar_search_url = similar_search_tag.attrs.get('href', None)
        if similar_search_url:
            kwargs['similar_search_url'] = urljoin(base_url, similar_search_url)
    # parsing: image guess
    image_guess_tag = search_page.select_one('._hUb a')
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
    tm_models = []
    if text_match_tags:
        for tag in text_match_tags:
            item = parse_text_match_html_tag(tag, base_url=base_url)
            tm_models.append(item)
    kwargs['TextMatch'] = tm_models
    return kwargs


def get_or_create_search_image(file_path=None, url=None, **kwargs):
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
    # alias
    models = gid.models

    base_url = 'https://www.google.com' if base_url is None else base_url
    session = models.db.session if session is None else session
    if not((file_path or url) and not (file_path and url)):
        raise ValueError('input url or file_path only')
    html_text = None
    search_url = None
    if file_path:
        searched_img_checksum = sha256_checksum(file_path)
        model, created = models.get_or_create(session, models.SearchImage, searched_img_checksum=searched_img_checksum)  # NOQA
    elif url:
        instance = models.SearchImage.query.filter_by(searched_img_url=url).first()
        model = None
        created = False
        if not instance:
            func_res = get_html_text_from_search_url(img_url=url)
            search_url = func_res['search_url']
            html_text = func_res['html_text']
            instance = models.SearchImage.query.filter_by(searched_img_url=url).first()
            if not instance:
                model, created = models.get_or_create(session, models.SearchImage, search_url=search_url, searched_img_url=url)  # NOQA
        if model is None:
            model = instance
        model.searched_img_url = url
    else:
        raise ValueError('Unknown condition, file path: {} url: {}'.format(file_path, url))
    if created or disable_cache:
        if file_path:
            search_url = get_search_url_from_img(file_path)
            func_res = get_html_text_from_search_url(search_url=search_url)
            html_text = func_res['html_text']
            search_url = func_res['search_url']
        if url and not html_text:
            func_res = get_html_text_from_search_url(img_url=url)
            html_text = func_res['html_text']
            search_url = func_res['search_url']
        search_page = BeautifulSoup(html_text, 'lxml')
        data = parse_img_search_html(search_page)
        model.search_url = search_url
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
                img_url_m = models.get_or_create(session, models.ImageURL, **img_url)[0]
                tags.extend([
                    {'namespace': 'page url', 'name': item['url']},
                    {'namespace': 'title', 'name': item['title']},
                    {'namespace': 'page url text', 'name': item['url_text']}
                ])
                add_tags_to_image_url(img_url_m, tags=tags, session=session)
                thumbnail_url_m = models.get_or_create(session, models.ImageURL, **thumbnail_url)[0]  # NOQA
                # text match img model
                item_m.img = models.get_or_create(
                    session, models.MatchResult, img_url=img_url_m, thumbnail_url=thumbnail_url_m)[0]  # NOQA
            model.text_matches.append(item_m)
        session.add(model)
    return model, created


def parse_text_match_html_tag(html_tag, base_url=None, session=None):
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
            {'namespace': 'imgres url', 'name': imgres_url},
        ]
        if imgref_url:
            img_url_tags.append({'namespace': 'page url', 'name': imgref_url})
            img_url_tags.append({'namespace': 'imgref url', 'name': imgref_url})
        kwargs['img_url_tags'] = img_url_tags
    return kwargs


def get_or_create_page_search_image(file_path=None, url=None, **kwargs):
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

    session = gid.models.db.session if session is None else session
    sm_model = get_or_create_search_image(file_path=file_path, url=url, disable_cache=disable_cache, session=session)[0]  # NOQA
    kwargs = {'search_img': sm_model, 'search_type': search_type, 'page': page}
    model, created = gid.models.get_or_create(session, gid.models.SearchImagePage, **kwargs)  # NOQA
    if created or disable_cache:
        gr_url = None
        if gid.models.SearchImagePage.TYPE_SIMILAR == search_type:
            gr_url = sm_model.similar_search_url
        elif gid.models.SearchImagePage.TYPE_SIZE == search_type:
            gr_url = sm_model.size_search_url
        else:
            log.error('Unknown search type: {}'.format(search_type))
        if not gr_url:
            session.add(sm_model)
            session.commit()
            raise gid.exceptions.NoResultFound('No url found for search type: {}'.format(search_type))  # NOQA
        user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'  # NOQA
        resp = requests.get(gr_url, headers={'User-Agent': user_agent}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        mr_models = []
        for html_tag in soup.select('.rg_bx'):
            mr_model, _ = get_or_create_match_result_from_html_soup(html_tag, session=session)
            mr_models.append(mr_model)
        model.match_results.extend(mr_models)
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

    session = gid.models.db.session if session is None else session
    thumb_folder = thumb_folder if thumb_folder else gid.models.DEFAULT_THUMB_FOLDER
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
    session = gid.models.db.session if session is None else session
    checksum = sha256_checksum(file_path)
    model, created = gid.models.get_or_create(
        session, gid.models.ImageFile, checksum=checksum)
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
