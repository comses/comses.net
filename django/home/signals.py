import logging

import shortuuid
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.models import Site as WagtailSite

from core.discourse import create_discourse_user
from core.models import EXCLUDED_USERNAMES, MemberProfile, SpamModeration

logger = logging.getLogger(__name__)


def sync_member_profile(user: User):
    mp, mp_created = MemberProfile.objects.get_or_create(user=user)
    if not mp_created:
        logger.warning("member profile already exists for user %s", user)
    return mp


def sync_discourse_user(user: User):
    response = create_discourse_user(user)
    # dont think we want to raise an exception
    # response.raise_for_status()
    data = response.json()
    success = data.get("success")
    if success:
        logger.debug("synced user %s with discourse: %s", user, data)
    else:
        logger.error("failed to sync user %s with discourse: %s", user, data)
    return success


def create_spam_moderation(mp: MemberProfile):
    content_type = ContentType.objects.get_for_model(type(mp))
    default_status = SpamModeration.Status.SCHEDULED_FOR_CHECK

    default_spam_moderation = {
        "status": default_status,
        "detection_method": "",
        "detection_details": "",
    }

    sm, created = SpamModeration.objects.update_or_create(
        content_type=content_type,
        object_id=mp.id,
        defaults=default_spam_moderation,
    )

    # update the related object
    mp.spam_moderation = sm
    mp.save()


@receiver(post_save, sender=User, dispatch_uid="member_profile_sync")
def on_user_save(sender, instance: User, created, **kwargs):
    """
    Ensure every created User has an associated MemberProfile
    """
    if instance.username in EXCLUDED_USERNAMES:
        return
    if created:
        mp = sync_member_profile(instance)
        if mp:
            create_spam_moderation(mp)
    if instance.email:
        # sync with discourse
        # to test discourse synchronization locally eliminate the DEPLOY_ENVIRONMENT check
        # but this will produce many test accounts if enabled in testing
        if not settings.DEPLOY_ENVIRONMENT.is_staging_or_production:
            return
        member_profile = instance.member_profile
        if member_profile.short_uuid:
            return
        else:
            member_profile.short_uuid = shortuuid.uuid()
            successful_discourse_sync = sync_discourse_user(instance)
            if successful_discourse_sync:
                member_profile.save()


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
