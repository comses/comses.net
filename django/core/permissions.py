from rest_framework import permissions

import logging

logger = logging.getLogger(__name__)


class ComsesPermissions(permissions.DjangoObjectPermissions):

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

    def has_permission(self, request, view):
        """
        Returns true iff this is a read-only request, delegates all other per-object responsibility
        to ObjectPermissionsBackend
        :param request:
        :param view:
        :return:
        """
        return request.method in permissions.SAFE_METHODS
