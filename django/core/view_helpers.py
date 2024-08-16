import logging
from django.core.exceptions import FieldError
from rest_framework.response import Response
from wagtail.search.backends import get_search_backend
from wagtail.contrib.search_promotions.models import Query
from wagtail.search.query import MATCH_ALL, Phrase
from wagtail.search.utils import parse_query_string

from .models import ComsesGroups

logger = logging.getLogger(__name__)

search_backend = get_search_backend()


def get_search_queryset(
    query, queryset, operator="or", fields=None, tags=None, criteria=None
):
    if not tags:
        tags = []

    if not criteria:
        criteria = {}

    order_by_relevance = not queryset.ordered

    """
    # FIXME: this won't work until RelatedFields support filtering
    # see https://docs.wagtail.io/en/stable/topics/search/indexing.html#index-relatedfields
    if tags:
        criteria.update(tags__name__in=[t.lower() for t in tags])
        operator = 'and'
    """

    if query:
        Query.get(query).add_hit()
        filters, query = parse_query_string(query, operator="or")
        criteria.update(filters)
    else:
        query = MATCH_ALL

    for tag in tags:
        query = query & Phrase(tag)

    if criteria:
        try:
            queryset = queryset.filter(**criteria)
        except FieldError:
            logger.warning("Invalid filter criteria: %s", criteria)

    logger.debug("parsed query: %s, filters: %s, fields: %s", query, criteria, fields)

    results = search_backend.search(
        query,
        queryset,
        operator=operator,
        fields=fields,
        order_by_relevance=order_by_relevance,
    )

    results.model = queryset.model
    return results


def retrieve_with_perms(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    data = serializer.data
    data = add_user_retrieve_perms(instance, data, request.user)
    return Response(data)


def add_user_retrieve_perms(instance, data, user):
    print(user.get_all_permissions())
    data["has_change_perm"] = user.has_perm(
        f"{instance._meta.app_label}.change_{instance._meta.model_name}",
        instance,
    )
    data["has_delete_perm"] = user.has_perm(
        f"{instance._meta.app_label}.delete_{instance._meta.model_name}",
        instance,
    )
    data["can_moderate"] = (
        user.is_superuser
        or ComsesGroups.MODERATOR.is_group_member(user)
    )
    return data
