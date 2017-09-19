from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin

import os

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
