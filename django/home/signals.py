import logging

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.wagtailcore.models import Site as WagtailSite

from core.models import MemberProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User, dispatch_uid='member_profile_creator')
def create_member_profile(sender, instance: User, created, **kwargs):
    """
    Ensures every created User has an associated MemberProfile as well
    :param sender: 
    :param instance: 
    :param created: 
    :param kwargs: 
    :return: 
    """
    if created:
        if instance.username in ('AnonymousUser',):
            # ignore anonymous user and
            return
        MemberProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=WagtailSite, dispatch_uid='wagtail_site_sync')
def sync_wagtail_sites(sender, instance: WagtailSite, created : bool, **kwargs):
    """
    Keeps default django.contrib.sites.models.Site in sync with the  richer wagtail.wagtailcore.models.Site instance.
    :param sender: 
    :param instance: 
    :param created: 
    :param kwargs: 
    :return: 
    """
    if instance.is_default_site and all([instance.site_name, instance.hostname]):
        site = Site.objects.first()
        site.name = instance.site_name
        site.domain = instance.hostname
        site.save()