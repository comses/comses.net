import logging
import shortuuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.models import Site as WagtailSite

from core.discourse import sync_discourseconnect_user
from core.models import MemberProfile, EXCLUDED_USERNAMES

logger = logging.getLogger(__name__)


def should_sync_discourse_user(user: User):
    return (
        settings.DEPLOY_ENVIRONMENT.is_staging_or_production
        and settings.DISCOURSE_SSO_SECRET
        and settings.DISCOURSE_SSO_SECRET != "unconfigured"
        and bool(user.email)
    )


def sync_member_profile(user: User):
    mp, mp_created = MemberProfile.objects.get_or_create(user=user)
    if not mp_created:
        logger.warning("member profile already exists for user %s", user)
    return mp


def sync_discourse_user(user: User):
    if not should_sync_discourse_user(user):
        return False

    member_profile = user.member_profile
    if not member_profile.short_uuid:
        member_profile.short_uuid = shortuuid.uuid()
        member_profile.save(update_fields=["short_uuid"])

    try:
        response = sync_discourseconnect_user(user)
        response.raise_for_status()
        data = response.json()
    except Exception:
        logger.exception("failed to sync user %s with discourse", user)
        return False

    if data.get("success"):
        logger.debug("synced user %s with discourse: %s", user, data)
        return True

    logger.error("failed to sync user %s with discourse: %s", user, data)
    return False


@receiver(post_save, sender=User, dispatch_uid="member_profile_sync")
def on_user_save(sender, instance: User, created, **kwargs):
    """
    Ensure every created User has an associated MemberProfile
    """
    if instance.username in EXCLUDED_USERNAMES:
        return
    if created:
        sync_member_profile(instance)
        return
    sync_discourse_user(instance)


@receiver(post_save, sender=MemberProfile, dispatch_uid="member_profile_discourse_sync")
def on_member_profile_save(sender, instance: MemberProfile, **kwargs):
    """
    Keep DiscourseConnect user data in sync when profile-backed fields change.
    """
    if instance.user.username in EXCLUDED_USERNAMES:
        return
    if kwargs.get("update_fields") == frozenset({"short_uuid"}):
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
