from urllib.parse import urlparse

from gbooru_images_download import models, api


class ModePlugin(api.ModePlugin):

    def get_match_results(self, search_term, page, session=None):
        if page != 1:
            raise NotImplementedError
        assert urlparse(search_term).scheme in ('http', 'https'), 'Unknown scheme'
        resp_model, resp = models.Response.create(
            search_term, 'get', session, requests_lib='requests_html', return_response=True)
        assert resp_model, 'Response failed: {}'.format(resp_model)
        pp = api.get_plugin_manager().getPluginByName('absolute_links', 'parser')
        match_results = list(
            pp.plugin_object.get_match_results(
                text=resp_model.text, response=resp, session=session, url=search_term))
        return match_results
