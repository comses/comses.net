import logging
import shortuuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.models import Site as WagtailSite

from core.discourse import create_discourse_user
from core.models import MemberProfile, EXCLUDED_USERNAMES

logger = logging.getLogger(__name__)


def sync_member_profile(user: User):
    suid = shortuuid.uuid()
    mp, mp_created = MemberProfile.objects.get_or_create(
        user=user, defaults={"short_uuid": suid}
    )
    if mp_created and not mp.short_uuid:
        mp.short_uuid = suid
        mp.save()

    return mp


def sync_discourse_user(user: User):
    response = create_discourse_user(user)
    # dont think we want to raise an exception
    # response.raise_for_status()
    data = response.json()
    if data.get("success"):
        logger.debug("synced user %s with discourse: %s", user, response.json())
    else:
        logger.error("failed to sync user %s with discourse: %s", user, response.json())


@receiver(post_save, sender=User, dispatch_uid="member_profile_sync")
def on_user_save(sender, instance: User, created, **kwargs):
    """
    Ensure every created User has an associated MemberProfile
    """
    if instance.username in EXCLUDED_USERNAMES:
        return
    if created:
        sync_member_profile(instance)
    # FIXME: discourse_username is a computed property, set it when we successfully sync with discourse instead?
    if instance.email and not instance.member_profile.discourse_username:
        # sync with discourse
        # to test discourse synchronization locally eliminate the DEPLOY_ENVIRONMENT check
        # but this will produce many test accounts if enabled in testing
        if not settings.DEPLOY_ENVIRONMENT.is_staging_or_production:
            return
        sync_discourse_user(instance)


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
