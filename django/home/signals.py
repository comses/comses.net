import logging
import shortuuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.core.models import Site as WagtailSite

from core.discourse import create_discourse_user
from core.models import MemberProfile, EXCLUDED_USERNAMES

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User, dispatch_uid="member_profile_sync")
def sync_user_member_profiles(sender, instance: User, created, **kwargs):
    """
    Ensure every created User has an associated MemberProfile
    """
    if created and instance.username not in EXCLUDED_USERNAMES:
        suid = shortuuid.uuid()
        mp, created = MemberProfile.objects.get_or_create(
            user=instance, defaults={"short_uuid": suid}
        )
        if created or not mp.short_uuid:
            mp.short_uuid = suid
            mp.save()


@receiver(post_save, sender=User, dispatch_uid="discourse_user_sync")
def sync_discourse_user(sender, instance: User, created, **kwargs):
    """Create a discourse user account when a user is created"""
    # to test discourse synchronization locally eliminate the DEPLOY_ENVIRONMENT check
    # but this will produce many test accounts if enabled in testing
    if (
        created
        and instance.username not in EXCLUDED_USERNAMES
        and settings.DEPLOY_ENVIRONMENT.is_staging_or_production()
    ):
        response = create_discourse_user(instance)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            logger.debug("synced user %s with discourse: %s", instance, response.json())
        else:
            logger.error(
                "failed to sync user %s with discourse: %s", instance, response.json()
            )


@receiver(post_save, sender=WagtailSite, dispatch_uid="wagtail_site_sync")
def sync_wagtail_django_sites(sender, instance: WagtailSite, created: bool, **kwargs):
    """
    Keep default django.contrib.sites.models.Site in sync with the wagtail.wagtailcore.models.Site instance.
    This is one-way only, so changes should typically be made to the WagtailSite model.
    """
    if instance.is_default_site and all([instance.site_name, instance.hostname]):
        site = Site.objects.first()
        site.name = instance.site_name
        site.domain = instance.hostname
        site.save()
