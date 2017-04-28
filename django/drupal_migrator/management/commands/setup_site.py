"""
Initialize Wagtail Models and other canned data.
"""

import logging

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite
from django.core.management.base import BaseCommand
from wagtail.wagtailcore.models import Page, Site

from home.models import LandingPage, FeaturedContentItem
from library.models import Codebase

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    """
    Creates a Wagtail Site object which is then mirrored by the Django.contrib Site via post_save signal
    """

    def add_arguments(self, parser):
        parser.add_argument('--site-name',
                            default='CoMSES Net',
                            help='Site human readable name, e.g., Network for Computational ...')
        parser.add_argument('--site-domain',
                            default='www.comses.net',
                            help='Site domain name, e.g., www.comses.net')

    def create_social_apps(self):
        site = DjangoSite.objects.first()
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

    def create_site(self, site_name, hostname, root_page):
        # FIXME: appears to be needed for signal handling despite docs that state it shouldn't be necessary
        # revisit and remove at some point if due to misconfiguration
        from django.apps import apps
        apps.get_app_config('home').ready()
        site = Site.objects.first() if Site.objects.count() > 0 else Site()
        site.site_name = site_name
        site.hostname = hostname
        site.is_default_site = True
        site.root_page = root_page
        site.save()
        return site

    def create_home_page(self):
        root_page = Page.objects.get(path='0001')
        # delete root page's initial children.
        root_page.get_children().delete()
        landing_page = LandingPage(
            title='CoMSES Net Home Page',
            slug='home',
            mission_statement='''CoMSES Net is an international network of researchers, educators 
            and professionals with the common goal of improving the way we develop, share, and
            use agent based modeling in the social and life sciences.
            ''')
        for codebase in Codebase.objects.filter(peer_reviewed=True):
            # if there are multiple images, just pull the first
            fc_dict = codebase.as_featured_content_dict()
            if fc_dict['image']:
                landing_page.featured_content_queue.add(FeaturedContentItem(**fc_dict))
        # refresh from DB before adding more nodes so treebeard can clean up its internal leaky abstraction
        # https://django-treebeard.readthedocs.io/en/latest/caveats.html
        root_page.refresh_from_db()
        root_page.add_child(instance=landing_page)
        return landing_page

    def handle(self, *args, **options):
        index_page = self.create_home_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'], root_page=index_page)
        self.create_social_apps()
