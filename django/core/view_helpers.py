import logging
import re

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from wagtail.search.backends import get_search_backend
from wagtail.search.models import Query

logger = logging.getLogger(__name__)

search_backend = get_search_backend()

VALID_ORDER_BY_PARAMS = ['date_created', 'last_modified']


def clean_order_by(order_by_params):
    for order_by_param in order_by_params:
        if not re.match(r'-?({})'.format('|'.join(VALID_ORDER_BY_PARAMS)), order_by_param):
            raise ValidationError(detail='Order by query parameter {} not valid. Must be zero or more of {}'
                                  .format(order_by_param, ', '.join(VALID_ORDER_BY_PARAMS)))
    return order_by_params


def get_search_queryset(query, queryset, operator="or", fields=None, tags=None, criteria=None):

    if query is None:
        query = ''

    if tags is None:
        tags = []

    lowercase_tags = " ".join([t.lower() for t in tags])
    results = queryset
    if query:
        if criteria:
            queryset = queryset.filter(**criteria)
        if tags:
            operator = 'and'
    query = f'{query} {lowercase_tags}'.strip()
    # this method is occasionally expected to serve as an identity function.
    # should look into refactoring at some point
    if query:
        results = search_backend.search(query, queryset, operator=operator, fields=fields)
        Query.get(query).add_hit()
    results.model = queryset.model
    return results


def retrieve_with_perms(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    data = serializer.data
    data = add_change_delete_perms(instance, data, request.user)
    return Response(data)


def add_change_delete_perms(instance, data, user):
    data['has_change_perm'] = user.has_perm('{}.change_{}'.format(instance._meta.app_label, instance._meta.model_name), instance)
    data['has_delete_perm'] = user.has_perm('{}.delete_{}'.format(instance._meta.app_label, instance._meta.model_name), instance)
    return data
