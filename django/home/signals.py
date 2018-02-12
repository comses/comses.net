import logging

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.wagtailcore.models import Site as WagtailSite

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
