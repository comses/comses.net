"""
Initialize Wagtail Models and other canned data.
"""

from allauth.socialaccount.models import SocialApp

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--site-name',
                            default='CoMSES Net',
                            help='Site human readable name, e.g., Network for Computational ...')
        parser.add_argument('--site-domain',
                            default='www.comses.net',
                            help='Site domain name, e.g., www.comses.net')

    def create_social_apps(self, site):
        if SocialApp.objects.count() == 0:
            orcid_app, created = SocialApp.objects.get_or_create(
                provider='orcid',
                name='ORCID',
                client_id=settings.ORCID_CLIENT_ID,
                secret=settings.ORCID_CLIENT_SECRET,
            )
            orcid_app.sites.add(site)
            github_app, created = SocialApp.objects.get_or_create(
                provider='github',
                name='GitHub',
                client_id=settings.GITHUB_CLIENT_ID,
                secret=settings.GITHUB_CLIENT_SECRET,
            )
            github_app.sites.add(site)

    def create_site(self, name, domain):
        # site.domain = 'test.comses.net'
        # site.name = 'CoRe at CoMSES.Net'
        # site.save()
        if Site.objects.count() > 0:
            site = Site.objects.first()
            site.name = name
            site.domain = domain
            site.save()
        else:
            site = Site.objects.create(name=name, domain=domain)
        return site

    def handle(self, *args, **options):
        site = self.create_site(options['site_name'], options['site_domain']) # dashes to underscores
        self.create_social_apps(site)
        # FIXME: create wagtail singleton landing pages
