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
        keywords = ('#', '.', '/')
        for a_tag in a_tags:
            href = a_tag.attrs.get('href', None)
            if href:
                if href.startswith(keywords) and url:
                    href = urljoin(url, href)
                elif href.startswith(keywords) and not url:
                    skipped_hrefs.append(href)
                url_model = models.get_or_create_url(session, value=href)[0]
                yield models.get_or_create(session, models.MatchResult, url=url_model)[0]
        if skipped_hrefs:
            log.debug('url', v=url)
            list(log.debug('href', v=x) for x in skipped_hrefs if x)
