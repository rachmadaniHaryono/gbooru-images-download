from urllib.parse import urlparse, urlencode, parse_qs
import json
import requests

import structlog
from bs4 import BeautifulSoup

from gbooru_images_download import models, api

log = structlog.getLogger(__name__)


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


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, search_term, page=1, session=None):
        json_resp = get_json_response(query=search_term.value, page=page)
        match_results = list(get_match_results(json_response=json_resp, session=session))
        return match_results
