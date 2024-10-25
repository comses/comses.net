import logging
from django.core.exceptions import FieldError
from rest_framework.response import Response
from wagtail.search.backends import get_search_backend
from wagtail.contrib.search_promotions.models import Query
from wagtail.search.query import (
    MATCH_ALL,
    Phrase,
    Boost,
    Or,
    Fuzzy,
    SearchQuery,
)

from itertools import combinations

from .models import ComsesGroups

logger = logging.getLogger(__name__)

# Define a list of stop words (prepositions, conjunctions, etc.)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


def build_search_query(input_text: str) -> SearchQuery:
    words = [word for word in input_text.split() if word.lower() not in STOP_WORDS]

    # Highest priority: Fuzzy match of the entire input text
    fuzzy_full_query = Boost(Fuzzy(input_text), boost=20.0)

    # Second priority: Exact match using Phrase
    exact_match_query = Boost(Phrase(input_text), boost=15.0)

    # Generate all 2-word combinations
    two_word_combos = list(combinations(words, 2))

    # Create queries for 2-word combinations
    two_word_queries = []
    for combo in two_word_combos:
        two_word_phrase = " ".join(combo)
        # Boost 2-word phrases higher if both words are in the original text
        if all(word in input_text for word in combo):
            two_word_queries.append(Boost(Phrase(two_word_phrase), boost=12.0))
        else:
            two_word_queries.append(Boost(Phrase(two_word_phrase), boost=3.0))

    # Make the search fuzzy using Fuzzy for individual words if word length > 3, otherwise use Phrase
    single_word_queries = [
        Fuzzy(word) if len(word) > 3 else Phrase(word) for word in words
    ]

    # Combine all queries
    all_queries = (
        [fuzzy_full_query, exact_match_query] + two_word_queries + single_word_queries
    )

    # Combine all queries using Or
    combined_query = Or(all_queries)

    return combined_query


def get_search_queryset(
    query,
    queryset,
    operator="or",
    fields=None,
    tags=None,
    criteria=None,
    order_by_relevance=False,
):
    search_backend = get_search_backend()

    if not fields:
        fields = []

    if not tags:
        tags = []

    if not criteria:
        criteria = {}

    """
    # FIXME: this won't work until RelatedFields support filtering
    # see https://docs.wagtail.io/en/stable/topics/search/indexing.html#index-relatedfields
    if tags:
        criteria.update(tags__name__in=[t.lower() for t in tags])
        operator = 'and'
    """

    """ 
    Build text search query
    """
    if query:
        Query.get(query).add_hit()

        # this can be used to create split query and filters from search field input text:
        # `some search terms peer_reviewed:True` -> query="some search terms" and filters=["peer_reviewed": True]
        # from wagtail.search.utils import parse_query_string
        # filters, query = parse_query_string(query, operator="and")
        # criteria.update(filters)

        query = build_search_query(query)
    else:
        query = MATCH_ALL

    # FIXME: tags should be better filters
    for tag in tags:
        query = query & Phrase(tag)

    """
    Set up order by relevance override for search
    other sort orders are handled by SmallResultSetPagination filtering and SORT_BY_FILTERS
    """
    """
    Filter queryset
    """
    if criteria:
        try:
            queryset = queryset.filter(**criteria)
        except FieldError as e:
            logger.warning("Invalid filter criteria:", exc_info=e)

    logger.debug(
        f"parsed query: {query}, filters: {criteria}, fields: {fields}, order_by_relevance: {order_by_relevance}"
    )

    """
    Perform wagtail search
    """
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
    data["can_moderate"] = user.is_superuser or ComsesGroups.is_moderator(user)
    return data
