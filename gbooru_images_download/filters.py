"""filter module."""
from flask_admin.contrib.sqla.filters import BaseSQLAFilter

from . import models


class MatchResultSearchQueryFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        res = query.filter(
            self.column.search_queries.contains(models.SearchQuery.query.get(value)))
        return res

    def operation(self):
        return 'equal'

    def get_options(self, view):
        return [
            (str(x.id), "'{}' page:{}".format(x.search_term.value, x.page))
            for x in models.SearchQuery.query.all()
        ]


class MatchResultFilteredUrlFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        # __import__('pdb').set_trace()
        filt_url_res = query.join('img_url').filter(models.ImageUrl.filtered)
        if value == '1':
            res = filt_url_res
        else:
            res = query.filter(
                models.MatchResult.id.notin_(
                    [x.id for x in filt_url_res.all() if hasattr(x, 'id')]))
        return res

    def operation(self):
        return 'in filter list'


class ThumbnailFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column.thumbnail_match_results.any())
        return query.filter(~self.column.thumbnail_match_results.any())

    def operation(self):
        return 'is thumbnail'


class FilteredImageUrl(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column.filtered)
        return query.filter(~self.column.filtered)

    def operation(self):
        return 'is filtered'


class TagFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        pass

    def operation(self):
        return 'contain'

    def get_options(self, view):
        return [
            (str(x.id), x.as_string)
            for x in models.Tag.query.all()
        ]
