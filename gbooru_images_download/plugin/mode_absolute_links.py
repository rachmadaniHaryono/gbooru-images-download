from urllib.parse import urlparse

from gbooru_images_download import models, api


class ModePlugin(api.ModePlugin):

    def get_match_results(
            self, search_term=None, page=1, text=None, response=None, session=None, url=None):
        if page != 1:
            raise NotImplementedError
        assert urlparse(search_term).scheme in ('http', 'https'), 'Unknown scheme'
        resp_model, resp = models.Response.create(
            search_term, 'get', session, requests_lib='requests_html', return_response=True)
        mr_dict = self.get_match_results_dict(
            text=text, response=response, session=session, url=url)
        match_results = self.match_results_models_from_dict(mr_dict, session)
        return match_results

    @classmethod
    def get_match_results_dict(cls, text=None, response=None, session=None, url=None):
        res = {'url': {}, 'tag': []}
        if not response:
            # TODO: create resp obj from text
            raise NotImplementedError
        links = response.html.absolute_links
        for link in links:
            if link not in res['url']:
                res['url'][link] = {'thumbnail': [], 'tag': []}
        return res
