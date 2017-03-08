import logging

logger = logging.getLogger(__name__)


class ComsesObjectPermissionBackend():
    """
    Authorization / Permissions backend that short-circuits if an object is "live", e.g., public or if the
    object's "submitter" property is the same as the user.
    """

    PUBLISHED_ATTRIBUTE_KEY = "live"
    OWNER_ATTRIBUTE_KEY = "submitter"

    def authenticate(self, username, password):
        return None

    @staticmethod
    def is_view_action(perm: str):
        """
        :param perm: string permission
        :return: Returns True if string permission defined by the perms_map in ComsesPermission corresponds to
        a GET request (e.g., contains "view_"), False otherwise
        """
        return 'view_' in perm

    def has_perm(self, user, perm, obj=None):
        """
        execute after admin / superuser checks in standard
        ModelBackend but right before django-guardian's ObjectPermissionBackend
        """
        logger.debug("checking if %s has perms %s on obj %s", user, perm, obj)
        if self.is_view_action(perm):
            return getattr(obj, self.PUBLISHED_ATTRIBUTE_KEY, True)
        # a write action, basic check to see if this user is the
        # submitter of the given object.
        return user == getattr(obj, self.OWNER_ATTRIBUTE_KEY, None)
