import logging
import re

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.functional import cached_property
from guardian.shortcuts import get_perms

from core.queryset import PUBLISHED_ATTRIBUTE_KEY, DELETABLE_ATTRIBUTE_KEY, OWNER_ATTRIBUTE_KEY

"""
Custom permission checking for models

Only add, change, delete and view permissions are handled by this layer.
Other permissions are handled by Django Guardian

Permissions must be between the ModelPermission backend and the Guardian backend.
"""

logger = logging.getLogger(__name__)


def is_object_action(perm: str):
    """
    :param perm: string permission
    :return: Returns True if the permission makes sense on an object
    """
    return 'change_' in perm or 'delete_' in perm or 'view_' in perm


def is_view_action(perm: str):
    """
    :param perm: string permission
    :return: Returns True if string permission defined by the perms_map in ComsesPermission corresponds to
    a GET request (e.g., contains "view_"), False otherwise
    """
    return 'view_' in perm


def is_delete_action(perm: str):
    return 'delete_' in perm


def get_model(perm):
    try:
        app_label, codename = perm.split('.')
    except ValueError:
        logger.error('Failed to split {}'.format(perm))
        raise
    permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
    return permission.content_type.model_class()


def has_authenticated_model_permission(user, perm, obj):
    if user.is_active and not is_object_action(perm):
        return True

    if obj is not None:
        return False

    if user.is_anonymous and not is_view_action(perm):
        raise PermissionDenied

    return False


def has_delete_permission(perm, obj):
    if is_delete_action(perm):
        deletable = getattr(obj, DELETABLE_ATTRIBUTE_KEY, True)
        if not deletable:
            raise PermissionDenied
    return False


def has_view_permission(perm, user, obj):
    """
    Users should have permission to view an object if it is published or they have any permission on the object
    This can be interpreted as having change or delete permission on an object implying that they have view permission
    on the object"""
    if is_view_action(perm):
        published = getattr(obj, PUBLISHED_ATTRIBUTE_KEY, True)
        if published:
            return True
        else:
            perms = get_perms(user, obj)
            return bool(perms)
    return False


def has_submitter_permission(user, obj):
    return user == getattr(obj, OWNER_ATTRIBUTE_KEY, None)


HANDLED_MODELS = set()


def add_to_comses_permission_whitelist(model):
    HANDLED_MODELS.add(model)
    return model


class ComsesObjectPermissionBackend:
    """
    Allow user that submitted the obj to perform any action with it
    """

    HANDLED_PERMS = re.compile('add_|change_|delete_|view_')

    def authenticate(self, request, username, password, **kwargs):
        return None

    def has_perm(self, user, perm, obj=None):
        """
        execute after admin / superuser checks in standard
        ModelBackend but right before django-guardian's ObjectPermissionBackend
        """
        if not user.is_active and not user.is_anonymous:
            raise PermissionDenied

        model = get_model(perm)
        if model in HANDLED_MODELS and re.search(self.HANDLED_PERMS, perm):
            return has_authenticated_model_permission(user, perm, obj) or \
                   has_delete_permission(perm, obj) or \
                   has_view_permission(perm, user, obj) or \
                   has_submitter_permission(user, obj)
        else:
            # Unhandled permissions are handled by the next permissions backend
            return False
