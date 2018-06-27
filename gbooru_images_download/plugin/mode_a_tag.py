from urllib.parse import urlparse

from gbooru_images_download import models, api


class ModePlugin(api.ModePlugin):

    def get_match_results(self, search_term, page, session=None):
        assert page == 1, 'Only support first page'
        assert urlparse(search_term).scheme in ('http', 'https'), 'Unknown scheme'
        resp_model = models.Response.create(search_term, 'get', session)
        assert resp_model, 'Response failed: {}'.format(resp_model)
        pp = api.get_plugin_manager().getPluginByName('Parser: a tag', 'parser')
        match_results = list(pp.plugin_object.get_match_results(resp_model.text, session, url=search_term))
        return match_results
