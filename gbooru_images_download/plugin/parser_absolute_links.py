import structlog

from gbooru_images_download import api


log = structlog.getLogger(__name__)


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, text=None, response=None, session=None, url=None):
        mr_dict = self.get_match_results_dict(
            text=text, response=response, session=session, url=url)
        res = self.match_results_model_from_dict(mr_dict, session)
        return res

    @classmethod
    def get_match_results_dict(cls, text=None, response=None, session=None, url=None):
        res = {'url': {}, 'tag': []}
        if not response:
            # TODO: create resp obj from text
            raise NotImplementedError
        for link in response.absolute_links:
            if link not in res['url']:
                res['url'][link] = {'thumbnail': [], 'tag': []}
        return res
