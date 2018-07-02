from urllib.parse import urlparse

from gbooru_images_download import models, api


class ModePlugin(api.ModePlugin):

    def get_match_results(self, search_term, page, session=None):
        assert page == 1, 'Only support first page'
        scheme = urlparse(search_term).scheme
        assert_msg = 'Unknown scheme: {}'.format(scheme)
        assert scheme in ('http', 'https'), assert_msg
        resp_model = models.Response.create(search_term, 'get', session)
        assert resp_model, 'Response failed: {}'.format(resp_model)
        pp = api.get_plugin_manager().getPluginByName('a tag', 'parser')
        match_results = list(
            pp.plugin_object.get_match_results(
                text=resp_model.text, session=session, url=search_term))
        return match_results
