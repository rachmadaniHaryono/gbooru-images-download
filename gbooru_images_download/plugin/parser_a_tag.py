from bs4 import BeautifulSoup
from gbooru_images_download import models, api


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, text, session=None):
        soup = BeautifulSoup(text, 'html.parser')
        a_tags = soup.select('a')
        pp = api.get_plugin_manager().getPluginByName('Parser: a tag on img tag', 'parser')
        mrs = list(pp.plugin_object.get_match_results(text, session))
        list(map(session.add, mrs))
        session.commit()
        for a_tag in a_tags:
            href = a_tag.attrs.get('href', None)
            if href:
                url_model = models.get_or_create(session, models.Url, value=href)[0]
                yield models.get_or_create(session, models.MatchResult, url=url_model)[0]
