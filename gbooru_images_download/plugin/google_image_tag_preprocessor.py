import structlog

from gbooru_images_download import api


log = structlog.getLogger(__name__)


class TagPreProcessor(api.TagPreProcessor):

    def run_tag_preprocessor(self, tags):
        # hide only: 'imgres url', 'msu', 'si'
        # regex:'id',
        invalid_namespace = ['cb', 'cl', 'cr', 'id', 'msm', 'rt', 'sm', 'tu', 'th', 'tw']
        nm_table = {
            'page url': api.Tag.page_url,
            'pt': api.Tag.picture_title,
            'ru': api.Tag.page_url,
            's': api.picture_subtitle,
            'st': api.Tag.site_title,
            'title': api.Tag.picture_title,
        }
        nm_copy_table = {
            'imgref url': api.Tag.page_url,
            'isu': api.Tag.site,
            'rh': api.Tag.site,
        }
        invalid_tags = (('s', ''), ('ity', ''), ('sc', '1'))
        for ns_val, tag_val in tags:
            if (ns_val, str(tag_val)) in invalid_tags:
                continue
            if not str(tag_val):
                log.debug('tag value is false', namespace=ns_val, value=tag_val)
                continue
            if ns_val in invalid_namespace:
                continue

            for key, value in nm_copy_table.items():
                if ns_val == key:
                    yield (value, tag_val)

            ns_replaced = False
            for key, value in nm_table.items():
                if key == ns_val:
                    yield (value, tag_val)
                    ns_replaced = True
                    break
            if not ns_replaced:
                yield (ns_val, tag_val)
