"""google image search."""
from urllib.parse import urlparse, urlencode, parse_qs
import json
import requests

import structlog
from bs4 import BeautifulSoup

from gbooru_images_download import models, api

log = structlog.getLogger(__name__)


def get_json_response(query, page=1):
    """get json response."""
    url_page = page - 1
    url_query = {
        'asearch': 'ichunk',
        'async': '_id:rg_s,_pms:s',
        # ei
        'ijn': str(url_page),
        'q': query,
        'start': str(int(url_page) * 100),
        'tbm': 'isch',
        # ved
        # vet
        # yv
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
    res['tag'].append((api.Namespace.imgres_url.value, imgres_url))
    res['tag'].append((api.Namespace.imgref_url.value, imgref_url))
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


def get_match_results(json_response=None, session=None):
    """Get match results."""
    session = models.db.session if session is None else session
    if json_response is not None:
        html = json_response[1][1]
        soup = BeautifulSoup(html, 'html.parser')
        for html_tag in soup.select('.rg_bx'):
            data = get_data(html_tag=html_tag)
            model = api.get_or_create_match_result(session=session, data=data)[0]
            session.add(model)
            yield model
    else:
        yield


class ModePlugin():
    """Base class for parser plugin."""

    def get_match_results(
            self, search_term=None, page=1, text=None, response=None, session=None, url=None):
        parsed_url = urlparse('https://www.google.com/search')
        url_query = {
            'asearch': 'ichunk',
            'async': '_id:rg_s,_pms:s,_fmt:pc',
            'ijn': str(page - 1),
            'q': search_term,
            'start': str(int(page - 1) * 100),
            'tbm': 'isch',
            'yv': '3',
        }
        query_url = parsed_url._replace(query=urlencode(url_query)).geturl()
        log.debug('query url', url=query_url)
        resp_model = models.Response.create(query_url, method='get', session=session)
        mr_dict = self.get_match_results_dict(
            text=resp_model.text, session=session, url=search_term)
        match_results = self.match_results_models_from_dict(mr_dict, session)
        return match_results

    @classmethod
    def get_match_results_dict(self, text=None, response=None, session=None, url=None):
        text = '<style>{}'.format(text.split('<style>', 1)[1])
        soup = BeautifulSoup(text, 'html.parser')
        res = {'url': {}, 'tag': []}
        rg_bx = soup.select('.rg_bx')
        for html_tag in rg_bx:
            rg_meta = json.loads(html_tag.select_one('div.rg_meta').text)
            url_tags = [
                ('gi {}'.format(key), str(value)) for key, value in rg_meta.items() if str(value)]
            url = rg_meta['ou']
            thumbnail = rg_meta['tu']
            if url in res['url']:
                res['url'][url]['tag'].extend(url_tags)
                res['url'][url]['thumbnail'].append(thumbnail)
            else:
                res['url'][url] = {'thumbnail': [thumbnail], 'tag': url_tags}
        return res
