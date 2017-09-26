import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import FieldDoesNotExist
from guardian import shortcuts as sc
from guardian.shortcuts import get_perms

logger = logging.getLogger(__name__)

OWNER_ATTRIBUTE_KEY = "submitter"
PUBLISHED_ATTRIBUTE_KEY = "live"
DELETABLE_ATTRIBUTE_KEY = 'deletable'


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


def is_delete_action(perm: str):
    return 'delete_' in perm


def has_authenticated_model_permission(user, perm, obj):
    if user.is_active and not is_object_action(perm):
        return True

    if obj is not None:
        return False

    if user.is_anonymous and not is_view_action(perm):
        raise PermissionDenied

    return True


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


def make_change_delete_view_perms(model):
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return ['{}.{}_{}'.format(app_label, action, model_name) for action in ['change', 'delete', 'view']]


def has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def get_db_user(user):
    """Replaces AnonymousUser with Guardian anonymous user db record. Otherwise returns input"""
    if user.is_anonymous:
        user = User.objects.get(username='AnonymousUser')
    return user


def get_viewable_objects_for_user(user, queryset):
    """A user can view an object in a list view if they have any permissions on the object
    (currently change, delete or view permission)"""
    model = queryset.model
    perms = make_change_delete_view_perms(model)
    kwargs = {}

    # Do not filter the queryset if the model does not have the PUBLISHED_ATTRIBUTE_KEY
    # (models without PUBLISHED_ATTRIBUTE_KEY are assumed to be live so are always included in list results)
    if has_field(model, PUBLISHED_ATTRIBUTE_KEY):
        user = get_db_user(user)
        kwargs[PUBLISHED_ATTRIBUTE_KEY] = True
        is_live_queryset = model.objects.filter(**kwargs)
        is_submitter_queryset = model.objects.filter(submitter=user)
        has_object_permission_queryset = sc.get_objects_for_user(user, perms=perms, any_perm=True,
                                                                 accept_global_perms=False)
        queryset &= has_object_permission_queryset | is_live_queryset | is_submitter_queryset

    return queryset


class EmailAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        l_username = username.lower().strip()
        try:
            user = User.objects.get(email=l_username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return super(EmailAuthenticationBackend, self).authenticate(request=request, username=username,
                                                                        password=password, **kwargs)


class ComsesObjectPermissionBackend:
    """
    Allow user that submitted the obj to perform any action with it
    """

    def authenticate(self, request, username, password, **kwargs):
        return None

    def has_perm(self, user, perm, obj=None):
        """
        execute after admin / superuser checks in standard
        ModelBackend but right before django-guardian's ObjectPermissionBackend
        """
        if not user.is_active and not user.is_anonymous:
            raise PermissionDenied

        return has_authenticated_model_permission(user, perm, obj) or \
            has_delete_permission(perm, obj) or \
            has_view_permission(perm, user, obj) or \
            has_submitter_permission(user, obj)
