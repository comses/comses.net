import logging

from rest_framework import permissions, exceptions

logger = logging.getLogger(__name__)


class ObjectPermissions(permissions.DjangoObjectPermissions):
    authenticated_users_only = False

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": [],
        "PATCH": [],
        "DELETE": [],
    }

    object_perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            "app_label": model_cls._meta.app_label,
            "model_name": model_cls._meta.model_name,
        }

        if method not in self.object_perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.object_perms_map[method]]


class ViewRestrictedObjectPermissions(ObjectPermissions):
    object_perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
