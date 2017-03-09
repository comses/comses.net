import logging
from django.core.exceptions import PermissionDenied
from guardian.shortcuts import get_objects_for_user

logger = logging.getLogger(__name__)

OWNER_ATTRIBUTE_KEY = "submitter"
PUBLISHED_ATTRIBUTE_KEY = "live"


def is_object_action(perm: str):
    """
    :param perm: string permission
    :return: Returns True if the permission makes sense on an object
    """
    return 'add_' not in perm


def is_view_action(perm: str):
    """
    :param perm: string permission
    :return: Returns True if string permission defined by the perms_map in ComsesPermission corresponds to
    a GET request (e.g., contains "view_"), False otherwise
    """
    return 'view_' in perm


def has_authenticated_model_permission(user, perm, obj):
    if user.is_active and not is_object_action(perm):
        return True

    if obj is not None:
        return False

    if user.is_anonymous and not is_view_action(perm):
        raise PermissionDenied

    return True


def has_view_permission(perm, obj):
    if is_view_action(perm):
        return getattr(obj, PUBLISHED_ATTRIBUTE_KEY, True)

    return False


def has_submitter_permission(user, obj):
    return user == getattr(obj, OWNER_ATTRIBUTE_KEY, None)


class ComsesObjectPermissionBackend:
    """
    Allow user that submitted the obj to perform any action with it
    """

    def authenticate(self, username, password):
        return None

    def has_perm(self, user, perm, obj=None):
        """
        execute after admin / superuser checks in standard
        ModelBackend but right before django-guardian's ObjectPermissionBackend
        """
        if not user.is_active and not user.is_anonymous:
            raise PermissionDenied

        return has_authenticated_model_permission(user, perm, obj) or \
               has_view_permission(perm, obj) or \
               has_submitter_permission(user, obj)
