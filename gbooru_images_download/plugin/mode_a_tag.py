from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
import structlog

from gbooru_images_download import models, api


log = structlog.getLogger(__name__)


class ModePlugin():

    def get_match_results(self, search_term, page, session=None):
        assert page == 1, 'Only support first page'
        scheme = urlparse(search_term).scheme
        assert_msg = 'Unknown scheme: {}'.format(scheme)
        assert scheme in ('http', 'https'), assert_msg
        resp_model = models.Response.create(search_term, 'get', session)
        mr_dict = self.get_match_results_dict(
            text=resp_model.text, session=session, url=search_term)
        match_results = self.match_results_models_from_dict(mr_dict, session)
        return match_results

    @classmethod
    def get_match_results_dict(cls, text=None, response=None, session=None, url=None):
        soup = BeautifulSoup(text, 'html.parser')
        res = {'url': {}, 'tag': []}
        a_tags = soup.select('a')
        skipped_hrefs = []
        keywords = ('#', '.', '/')
        for a_tag in a_tags:
            tag = []
            href = a_tag.attrs.get('href', None)
            if href:
                if href.startswith(keywords) and url:
                    href = urljoin(url, href)
                elif href.startswith(keywords) and not url:
                    skipped_hrefs.append(href)
                for key, value in a_tag.attrs.items():
                    if key == 'href':
                        pass
                    elif key == 'target' and value == '_blank':
                        pass
                    elif isinstance(value, list):
                        for sub_value in value:
                            tag.append(('a tag {}'.format(key), sub_value))
                    else:
                        tag.append(('a tag {}'.format(key), value))
                if href not in res['url']:
                    res['url'][href] = {'thumbnail': [], 'tag': tag}
                else:
                    for sub_tag in tag:
                        if sub_tag not in res['url'][href]['tag']:
                            res['url'][href]['tag'].append(sub_tag)
        if skipped_hrefs:
            log.debug('url', v=url)
            list(log.debug('href', v=x) for x in skipped_hrefs if x)
        return res
