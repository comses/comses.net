import logging
from collections import OrderedDict
from dateutil import parser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.conf import settings
from collections import defaultdict

logger = logging.getLogger(__name__)


SORT_BY_FILTERS = defaultdict(
    lambda: "Sort by: Relevance",  # default sort by relevance
    {
        "-first_published_at": "Sort by: Publish date: newest",
        "first_published_at": "Sort by: Publish date: oldest",
        "-last_modified": "Sort by: Recently Modified",
    },
)


class SmallResultSetPagination(PageNumberPagination):
    max_result_window = 2500
    page_size = 10
    page_size_query_param = "page_size"

    @staticmethod
    def _to_search_terms(query_params):
        return [f"{k}: {v}" for k, v in query_params.lists()]

    @staticmethod
    def _to_filter_display_terms(query_params):
        """
        Convert query parameters into a list of displayable filter terms.
        Args:
            query_params (QueryDict): The query parameters.
        Returns:
            list: A list of display filter terms.
        """
        filters = []
        for key, values in query_params.lists():
            if key == "query":
                continue
            elif key == "ordering":
                filters.extend(SORT_BY_FILTERS[v] for v in values)
            elif key == "tags":
                filters.extend(values)
            elif key in ["published_before", "published_after"]:
                try:
                    date = parser.isoparse(values[0]).date()
                    filters.append(f"{key.replace('_', ' ')} {date.isoformat()}")
                except ValueError:
                    filters.extend(v.replace("_", " ") for v in values)
            else:
                filters.extend(v.replace("_", " ") for v in values)
        return filters

    @classmethod
    def limit_page_range(cls, page=1, count=max_result_window, size=page_size):
        try:
            es_settings = getattr(settings, "WAGTAILSEARCH_BACKENDS", {})
            max_result_window = es_settings["default"]["INDEX_SETTINGS"]["settings"][
                "index"
            ]["max_result_window"]
        except KeyError as e:
            logger.warning(
                "max_result_window not set for Elasticsearch, setting to default %s",
                cls.max_result_window,
                exc_info=e,
            )
            max_result_window = cls.max_result_window

        # limit the result count to max_result_window
        limited_count = min(count, max_result_window)

        # Clamp page to range [1, max_page_number]
        try:
            max_page_number = -(-limited_count // size)
            limited_page_number = min(max(1, int(page)), max_page_number)
        except ValueError:
            limited_page_number = 1

        return limited_count, limited_page_number

    def get_paginated_response(self, data):
        context = self.get_context_data(data)
        return Response(context)

    @classmethod
    def create_paginated_context_data(
        cls, query, data, page, count, query_params, size=None
    ):
        """
        Creates the paginated context data for jinja search templates

        Args:
            query: request query
            data: results from Elasticsearch
            page: requested page (typically from http query params)
            count: total number of results
            query_params: query dictionary
            size (optional): number of results per page, defaults to cls.page_size (currently: 10)

        Returns:
            dict: paginated context data
        """
        if size is None:
            size = cls.page_size

        limited_count, limited_page_number = cls.limit_page_range(page, count, size)

        # ceiling division https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python
        num_pages = -(-limited_count // size)

        page_range = list(
            range(
                max(2, limited_page_number - 3), min(num_pages, limited_page_number + 4)
            )
        )

        num_results = 0

        if limited_count != 0:
            num_results = min(size, limited_count - (limited_page_number - 1) * size)

        return OrderedDict(
            {
                "is_first_page": limited_page_number == 1,
                "is_last_page": limited_page_number == num_pages,
                "current_page": limited_page_number,
                "num_results": num_results,
                "count": limited_count,
                "query": query,
                "search_terms": cls._to_search_terms(query_params),
                "filter_display_terms": cls._to_filter_display_terms(query_params),
                "query_params": query_params.urlencode(),
                "range": page_range,
                "num_pages": num_pages,
                "results": data,
            }
        )

    def get_context_data(self, data):
        query_params = self.request.query_params.copy()
        query = query_params.get("query")
        page = query_params.pop("page", [1])[0]

        count = self.page.paginator.count

        return self.create_paginated_context_data(
            query=query,
            data=data,
            page=page,
            count=count,
            query_params=query_params,
        )
