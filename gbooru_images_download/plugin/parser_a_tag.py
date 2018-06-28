from urllib.parse import urljoin

from bs4 import BeautifulSoup
import structlog

from gbooru_images_download import models, api


log = structlog.getLogger(__name__)


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, text, session=None, url=None):
        soup = BeautifulSoup(text, 'html.parser')
        a_tags = soup.select('a')
        pp = api.get_plugin_manager().getPluginByName('a tag on img tag', 'parser')
        mrs = list(pp.plugin_object.get_match_results(text, session, url=url))
        list(map(session.add, mrs))
        session.commit()
        skipped_hrefs = []
        for a_tag in a_tags:
            href = a_tag.attrs.get('href', None)
            if href:
                if href.startswith(('#', '.')) and url:
                    href = urljoin(url, href)
                elif href.startswith(('#', '.')) and not url:
                    skipped_hrefs.append(href)
                url_model = models.get_or_create(session, models.Url, value=href)[0]
                yield models.get_or_create(session, models.MatchResult, url=url_model)[0]
        if skipped_hrefs:
            log.debug('url', v=url)
            list(map(lambda x: log.debug('href', v=x), skipped_hrefs))
