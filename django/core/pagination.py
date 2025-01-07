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
        "-first_published_at": "Sort by: Recently published",
        "first_published_at": "Sort by: Earliest published",
        "-last_modified": "Sort by: Recently modified",
        "last_modified": "Sort by: Earliest modified",
        "-date_created": "Sort by: Recently created",
        "date_created": "Sort by: Earliest created",
        "start_date": "Sort by: Start date",
        "submission_deadline": "Sort by: Submission deadline",
        "early_registration_deadline": "Sort by: Early registration deadline",
        "application_deadline": "Sort by: Application deadline",
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
        Convert query parameters into a list of displayable filter terms (replaces underscores withs spaces, etc)
        Args:
            query_params (QueryDict): The query parameters.
        Returns:
            list: A list of displayable filter terms.
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
                    publication_date = parser.isoparse(values[0]).date()
                    filters.append(
                        f"{key.replace('_', ' ')} {publication_date.isoformat()}"
                    )
                except ValueError:
                    # FIXME: this default behavior duplicates what we want to do in the else clause below
                    filters.extend(v.replace("_", " ") for v in values)
            else:
                filters.extend(v.replace("_", " ") for v in values)
        return filters

    @classmethod
    def limit_page_range(cls, page=1, count=None, size=None):
        """
        Limits the page range based on the maximum result window and page size.

        This method ensures that the page number and result count do not exceed
        the configured maximum result window for Elasticsearch. It also clamps
        the page number to a valid range.

        Args:
            page (int): The current page number. Defaults to 1.
            count (int): The total number of results. Defaults to max_result_window.
            size (int): The number of results per page. Defaults to page_size.

        Returns:
            tuple: A tuple containing:
                - limited_count (int): The total number of results to be shown in the current page, clamped to max_result_window.
                - limited_page_number (int): The clamped page number within the valid range.
        """
        if count is None:
            count = cls.max_result_window
        if size is None:
            size = cls.page_size
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

        # Clamp page to range [1, max_page]
        try:
            max_page = (limited_count + size - 1) // size
            requested_page = max(1, int(page))
            limited_page_number = min(requested_page, max_page)
        except ValueError:
            limited_page_number = 1

        logger.debug(
            "Clamping count to %s and requested page to %s",
            limited_count,
            limited_page_number,
        )
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
