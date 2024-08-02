import logging
from collections import OrderedDict
from dateutil import parser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.conf import settings

logger = logging.getLogger(__name__)


class SmallResultSetPagination(PageNumberPagination):
    max_result_window = 2500
    page_size = 10
    page_size_query_param = "page_size"

    @staticmethod
    def _to_search_terms(query_params):
        return [f"{k}: {v}" for k, v in query_params.lists()]

    @staticmethod
    def _to_filter_display_terms(query_params):
        filters = []
        for key, values in query_params.lists():
            if key == "query":
                continue
            elif key == "ordering":
                for v in values:
                    if v == "":
                        filters.append("Sort by: Relevance")
                    elif v == "-first_published_at":
                        filters.append("Sort by: Publish date: newest")
                    elif v == "first_published_at":
                        filters.append("Sort by: Publish date: oldest")
                    elif v == "-last_modified":
                        filters.append("Sort by: Recently Modified")
            elif key == "tags":
                filters.extend(tag for tag in values)
            else:
                try:
                    date = parser.isoparse(values[0]).date()
                    filters.append(f"{key.replace('_', ' ')} {date.isoformat()}")
                except ValueError:
                    filters.extend(v.replace("_", " ") for v in values)

        return filters

    @classmethod
    def limit_page_range(cls, page=1, count=max_result_window, size=page_size):
        try:
            es_settings = getattr(settings, "WAGTAILSEARCH_BACKENDS", {})
            max_result_window = (
                es_settings.get("default", {})
                .get("INDEX_SETTINGS", {})
                .get("settings", {})
                .get("index", {})
                .get("max_result_window", cls.max_result_window)
            )

            logger.info(f"max_result_window from settings: {max_result_window} ")
        except Exception as e:
            logger.info("max_result_window not set for Elasticsearch: %s", e)

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
            current_page_number: request parameter
            count: total number of results
            query_params: query dictionary
            size (optional): number of results per page (default=cls.page_size)

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
