import logging
import shortuuid

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.models import Site as WagtailSite

from core.discourse import sync_discourse_user
from core.models import MemberProfile, EXCLUDED_USERNAMES

logger = logging.getLogger(__name__)


@transaction.atomic
def sync_member_profile(user: User):
    mp, mp_created = MemberProfile.objects.get_or_create(user=user)
    if not mp.short_uuid:
        mp.short_uuid = shortuuid.uuid()
        mp.save()
    if not mp_created:
        logger.warning("member profile already exists for user %s", user)
    return mp


# Fields on User that are part of the Discourse SSO sync payload
# (email, username, and name via first_name/last_name).
DISCOURSE_SYNC_USER_FIELDS = frozenset({"email", "username", "first_name", "last_name"})

# Fields on MemberProfile that are part of the Discourse SSO sync payload
# (short_uuid as external_id, picture for avatar_url).
DISCOURSE_SYNC_MEMBER_PROFILE_FIELDS = frozenset({"short_uuid", "picture"})


@receiver(post_save, sender=User, dispatch_uid="member_profile_sync")
def on_user_save(sender, instance: User, created, update_fields=None, **kwargs):
    """
    Ensure every created User has an associated MemberProfile and keep
    DiscourseConnect user data in sync when User-backed payload fields change.
    """
    if instance.username in EXCLUDED_USERNAMES:
        return
    if created:
        sync_member_profile(instance)
        return
    if update_fields is not None:
        if not update_fields.intersection(DISCOURSE_SYNC_USER_FIELDS):
            return
    sync_discourse_user(instance)


@receiver(post_save, sender=MemberProfile, dispatch_uid="member_profile_discourse_sync")
def on_member_profile_save(
    sender, instance: MemberProfile, update_fields=None, **kwargs
):
    """
    Keep DiscourseConnect user data in sync when profile-backed fields change.

    The Discourse SSO payload only includes ``short_uuid`` (external_id) and
    ``avatar_url`` (derived from ``picture``) from MemberProfile. The remaining
    payload fields (email, username, name) come from the related User and are
    handled by the ``on_user_save`` receiver. Skip the sync when the saved
    fields are known and none of them affect the payload.
    """
    if instance.username in EXCLUDED_USERNAMES:
        return
    if update_fields is not None:
        if not update_fields.intersection(DISCOURSE_SYNC_MEMBER_PROFILE_FIELDS):
            return
    sync_discourse_user(instance.user)


@receiver(post_save, sender=WagtailSite, dispatch_uid="wagtail_site_sync")
def sync_wagtail_django_sites(sender, instance: WagtailSite, created: bool, **kwargs):
    """
    Keep default django.contrib.sites.models.Site in sync with the wagtail.models.Site instance.
    This is one-way only, so changes should only be made to the WagtailSite model.
    """
    if instance.is_default_site and all([instance.site_name, instance.hostname]):
        site = Site.objects.first()
        site.name = instance.site_name
        site.domain = instance.hostname
        site.save()
