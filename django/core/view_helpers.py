import logging
import os
import re

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from guardian.decorators import permission_required_or_403
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from wagtail.wagtailsearch.backends import get_search_backend

from core.backends import get_viewable_objects_for_user

logger = logging.getLogger(__name__)

search = get_search_backend()


def create_edit_routes(prefix: str, model, lookup_field: str, lookup_regex: str):
    base_url = r'^{prefix}/(?P<{lookup_field}>{lookup_regex})/'.format(prefix=prefix, lookup_field=lookup_field,
                                                                       lookup_regex=lookup_regex)
    update_form_url = base_url + 'update/$'
    create_form_url = '^' + prefix + '/create/$'

    app_name = model._meta.app_label
    base_name = model._meta.object_name.lower()
    template_name = os.path.join(app_name, prefix, 'create_or_update.jinja')

    perm = app_name + '.change_' + base_name

    create_view = login_required()(TemplateView.as_view(template_name=template_name))
    update_view = permission_required_or_403(perm, (model, lookup_field, lookup_field))(
        TemplateView.as_view(template_name=template_name))

    return [
        url(update_form_url, update_view,
            name='{base_name}-update'.format(base_name=base_name)),
        url(create_form_url, create_view,
            name='{base_name}-create'.format(base_name=base_name)),
    ]


VALID_ORDER_BY_PARAMS = ['date_created', 'last_modified']


def clean_order_by(order_by_params):
    for order_by_param in order_by_params:
        if not re.match(r'-?({})'.format('|'.join(VALID_ORDER_BY_PARAMS)), order_by_param):
            raise ValidationError(detail='Order by query parameter {} not valid. Must be zero or more of {}'
                                  .format(order_by_param, ', '.join(VALID_ORDER_BY_PARAMS)))
    return order_by_params


def get_search_queryset(self):
    """
    FIXME: this is broken, as not every linked entity will have a `date_created` field
    give this a parameterizable ordering field instead
    :param self:
    :return:
    """
    query = self.request.query_params.get('query')
    tags = self.request.query_params.getlist('tags')
    order_by = clean_order_by(self.request.query_params.getlist('order_by'))
    has_order_by = bool(order_by)
    if not order_by:
        order_by = ['-date_created']

    user = self.request.user

    queryset = self.queryset
    for tag in tags:
        queryset = queryset.filter(tags__name=tag)
    queryset = get_viewable_objects_for_user(user, queryset)
    queryset = queryset.order_by(*order_by)

    if query:
        model = queryset.model
        # Order by relevance if no order_by param was present
        queryset = search.search(query, queryset, order_by_relevance=has_order_by)
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
