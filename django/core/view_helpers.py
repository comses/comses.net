import logging
import re

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from wagtail.wagtailsearch.backends import get_search_backend

logger = logging.getLogger(__name__)

search = get_search_backend()

VALID_ORDER_BY_PARAMS = ['date_created', 'last_modified']


def clean_order_by(order_by_params):
    for order_by_param in order_by_params:
        if not re.match(r'-?({})'.format('|'.join(VALID_ORDER_BY_PARAMS)), order_by_param):
            raise ValidationError(detail='Order by query parameter {} not valid. Must be zero or more of {}'
                                  .format(order_by_param, ', '.join(VALID_ORDER_BY_PARAMS)))
    return order_by_params


def get_search_queryset(query, queryset, order_by_relevance=True):
    model = queryset.model
    queryset = search.search(query, queryset, order_by_relevance=order_by_relevance)
    # Need get_queryset method to work on DRF viewsets
    # DRF viewsets have permissions which require get_queryset to return something that has a model property
    queryset.model = model
    return queryset


def retrieve_with_perms(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    data = serializer.data
    data = add_change_delete_perms(instance, data, request.user)
    return Response(data)


def add_change_delete_perms(instance, data, user):
    data['has_change_perm'] = user.has_perm('change_' + instance._meta.model_name, instance)
    data['has_delete_perm'] = user.has_perm('delete_' + instance._meta.model_name, instance)
    return data
