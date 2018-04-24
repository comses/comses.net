import logging

from rest_framework import permissions

logger = logging.getLogger(__name__)


class AllowUnauthenticatedPermissions(permissions.DjangoObjectPermissions):
    authenticated_users_only = False


class AllowUnauthenticatedViewPermissions(permissions.DjangoObjectPermissions):
    authenticated_users_only = False

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }
