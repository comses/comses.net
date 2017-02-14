from rest_framework.permissions import BasePermission, SAFE_METHODS


class PermissionMixin:

    def has_edit_permission(self, user):
        return self.owner == user


class IsEditable(BasePermission):
    """All models must have a has_edit_permission method"""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return obj.has_edit_permission(request.user)