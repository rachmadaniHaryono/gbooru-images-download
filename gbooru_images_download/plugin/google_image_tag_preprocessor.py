import structlog

from gbooru_images_download.api import Namespace, TagPreProcessor


log = structlog.getLogger(__name__)


class TagPreProcessor(TagPreProcessor):

    def run_tag_preprocessor(self, tags):
        # hide only: 'imgres url', 'msu', 'si'
        # regex:'id',
        invalid_namespace = ['cb', 'cl', 'cr', 'id', 'msm', 'rt', 'sm', 'tu', 'th', 'tw']
        nm_table = {
            'page url': Namespace.page_url.value,
            'pt': Namespace.picture_title.value,
            'ru': Namespace.page_url.value,
            's': Namespace.picture_subtitle.value,
            'st': Namespace.site_title.value,
            'title': Namespace.picture_title.value,
        }
        nm_copy_table = {
            'imgref url': Namespace.page_url.value,
            'isu': Namespace.site.value,
            'rh': Namespace.site.value,
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
