from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from guardian import shortcuts as sc


def make_change_delete_view_perms(model):
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return ['{}.{}_{}'.format(app_label, action, model_name) for action in ['change', 'delete', 'view']]


def get_viewable_objects_for_user(user, queryset):
    """A user can view an object in a list view if they have any permissions on the object
    (currently change, delete or view permission)"""
    model = queryset.model
    perms = make_change_delete_view_perms(model)

    # Do not filter the queryset if the model does not have the PUBLISHED_ATTRIBUTE_KEY
    # (models without PUBLISHED_ATTRIBUTE_KEY are assumed to be live so are always included in list results)
    if hasattr(model, 'HAS_PUBLISHED_KEY') or has_field(model, PUBLISHED_ATTRIBUTE_KEY):
        user = get_db_user(user)
        is_public_queryset = queryset.public()
        is_submitter_queryset = queryset.filter(submitter=user)
        has_object_permission_queryset = sc.get_objects_for_user(user, perms=perms, any_perm=True,
                                                                 accept_global_perms=False, klass=queryset)
        queryset &= has_object_permission_queryset | is_public_queryset | is_submitter_queryset

    return queryset


PUBLISHED_ATTRIBUTE_KEY = "live"
DELETABLE_ATTRIBUTE_KEY = 'deletable'
OWNER_ATTRIBUTE_KEY = "submitter"


def get_db_user(user):
    """Replaces AnonymousUser with Guardian anonymous user db record. Otherwise returns input"""
    if user.is_anonymous:
        user = User.objects.get(username='AnonymousUser')
    return user


def has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False
