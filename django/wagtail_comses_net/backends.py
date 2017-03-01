from django.db import models
from django.contrib.auth.models import AnonymousUser

class ComsesObjectPermissionBackend(object):
    def authenticate(self, username, password):
        return None

    @staticmethod
    def get_action(perm):
        unnamespaced_perm = perm.rsplit('.', 1)[1]
        action = unnamespaced_perm.split('_', 1)[0]
        return action

    @staticmethod
    def get_view_perm(obj: models.Model):
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        return "{}.view_{}".format(app_label, model_name)

    def has_view_perm(self, user_obj, perm, obj):
        if perm != self.get_view_perm(obj):
            return False

        # Give permission to anyone that has global view permission
        has_permission = self.get_view_perm(obj) in user_obj.get_all_permissions()
        if obj.live:
            return has_permission
        else:
            return False

    def has_perm(self, user_obj, perm, obj=None):
        if user_obj.is_anonymous() and self.get_action(perm) == 'view':
            if obj:
                return obj.live
            else:
                return True
        if not user_obj.is_active:
            return False
        if not obj:
            return False
        return user_obj == obj.submitter or \
               self.has_view_perm(user_obj, perm, obj)
