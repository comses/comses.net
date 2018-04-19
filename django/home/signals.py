import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.core.models import Site as WagtailSite

from core.discourse import create_discourse_user
from core.models import MemberProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User, dispatch_uid='member_profile_sync')
def sync_user_member_profiles(sender, instance: User, created, **kwargs):
    """
    Ensure every created User has an associated MemberProfile
    """
    if created and instance.username not in ('AnonymousUser',):
        # ignore anonymous user
        MemberProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User, dispatch_uid='discourse_user_sync')
def sync_discourse_user(sender, instance: User, created, **kwargs):
    """Create a discourse user account when a user is created"""

    # if you want to test discourse synchronization locally you could eliminate the DEPLOY_ENVIRONMENT check
    # note: this will produce many test accounts if enabled in testing
    is_staging_or_production = settings.DEPLOY_ENVIRONMENT.is_production() or settings.DEPLOY_ENVIRONMENT.is_staging()
    if created and instance.username not in ('AnonymousUser',) and is_staging_or_production:
        response = create_discourse_user(instance)
        response.raise_for_status()
        data = response.json()
        if data.get('success', False):
            logger.error('Failed syncing user {} to discourse. Got payload of {}.'.format(instance, response.json()))
        else:
            logger.debug('Syncing user {} to discourse. Got payload of {}.'.format(instance, response.json()))


@receiver(post_save, sender=WagtailSite, dispatch_uid='wagtail_site_sync')
def sync_wagtail_django_sites(sender, instance: WagtailSite, created: bool, **kwargs):
    """
    Keep default django.contrib.sites.models.Site in sync with the wagtail.wagtailcore.models.Site instance.
    """
    if instance.is_default_site and all([instance.site_name, instance.hostname]):
        site = Site.objects.first()
        site.name = instance.site_name
        site.domain = instance.hostname
        site.save()
