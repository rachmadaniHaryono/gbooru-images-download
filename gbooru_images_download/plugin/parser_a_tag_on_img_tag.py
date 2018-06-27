from bs4 import BeautifulSoup
from gbooru_images_download import models, api


class ParserPlugin(api.ParserPlugin):

    def get_match_results(self, text, session=None):
        soup = BeautifulSoup(text, 'html.parser')
        a_tags = soup.select('a')
        session.commit()
        for a_tag in a_tags:
            href = a_tag.attrs.get('href', None)
            if not href:
                continue
            for img_tag in a_tag.select('img'):
                img_src = img_tag.get('src', None)
                if img_src:
                    url_model = models.get_or_create(
                        session, models.Url, value=href)[0]
                    img_url_model = models.get_or_create(
                        session, models.Url, value=img_src)[0]
                    yield models.get_or_create(
                        session, models.MatchResult, url=url_model, thumbnail_url=img_url_model)[0]
