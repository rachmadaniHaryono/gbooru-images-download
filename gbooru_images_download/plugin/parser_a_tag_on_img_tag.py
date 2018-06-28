from urllib.parse import urljoin

from bs4 import BeautifulSoup
import structlog

from gbooru_images_download import models, api


log = structlog.getLogger(__name__)


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, text, session=None, url=None):
        soup = BeautifulSoup(text, 'html.parser')
        a_tags = soup.select('a')
        session.commit()
        skipped_hrefs = []
        skipped_img_src = []
        for a_tag in a_tags:
            href = a_tag.attrs.get('href', None)
            if href.startswith(('#', '.')):
                href = urljoin(url, href)
            elif href.startswith(('#', '.')) and not url:
                skipped_hrefs.append(href)
            if not href:
                skipped_hrefs.append(href)
            for img_tag in a_tag.select('img'):
                img_src = img_tag.get('src', None)
                if img_src:
                    if img_src.startswith(('#', '.')):
                        img_src = urljoin(url, img_src)
                    elif img_src.startswith(('#', '.')) and not url:
                        skipped_img_src.append(img_src)
                    url_model = models.get_or_create(
                        session, models.Url, value=href)[0]
                    img_url_model = models.get_or_create(
                        session, models.Url, value=img_src)[0]
                    yield models.get_or_create(
                        session, models.MatchResult, url=url_model, thumbnail_url=img_url_model)[0]

        if any(skipped_hrefs, skipped_img_src):
            log.debug('url', v=url)
            list(map(lambda x: log.debug('href', v=x), skipped_hrefs))
            list(map(lambda x: log.debug('img src:', v=x), skipped_img_src))
