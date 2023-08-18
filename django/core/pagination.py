import logging
from collections import OrderedDict
from dateutil import parser

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200

    @staticmethod
    def _to_search_terms(query_params):
        return [f"{k}: {v}" for k, v in query_params.lists()]

    @staticmethod
    def _to_filter_display_terms(query_params):
        filters = []
        for key, values in query_params.lists():
            if key == "query":
                continue
            if key == "tags":
                filters.extend(tag for tag in values)
            else:
                try:
                    date = parser.isoparse(values[0]).date()
                    filters.append(f"{key.replace('_', ' ')} {date.isoformat()}")
                except ValueError:
                    filters.extend(v.replace("_", " ") for v in values)

        return filters

    def get_paginated_response(self, data):
        context = self.get_context_data(data)
        return Response(context)

    @classmethod
    def create_paginated_context_data(
        cls, query, data, current_page_number, count, query_params, size=None
    ):
        if size is None:
            size = cls.page_size
        # ceiling division https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python
        num_pages = -(-count // size)
        page_range = list(
            range(
                max(2, current_page_number - 3), min(num_pages, current_page_number + 4)
            )
        )
        return OrderedDict(
            {
                "is_first_page": current_page_number == 1,
                "is_last_page": current_page_number == num_pages,
                "current_page": current_page_number,
                "num_results": min(size, count - (current_page_number - 1) * size),
                "count": count,
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
        try:
            current_page_number = max(1, int(page))
        except ValueError:
            current_page_number = 1
        return self.create_paginated_context_data(
            query=query,
            data=data,
            current_page_number=current_page_number,
            count=count,
            query_params=query_params,
        )
