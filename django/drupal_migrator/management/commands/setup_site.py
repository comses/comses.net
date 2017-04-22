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
        site = Site.objects.first() if Site.objects.count() > 0 else Site()
        site.site_name = site_name
        site.hostname = hostname
        site.is_default_site = True
        site.root_page = root_page
        site.save()
        return site

    def create_home_page(self):
        if LandingPage.objects.count() > 0:
            LandingPage.objects.delete()
        root_page = Page.objects.get(pk=1)
        logger.debug("attaching to root page %s", root_page)
        # delete initial welcome page
        Page.objects.filter(slug='home').delete()
        landing_page = LandingPage(title='CoMSES Net Home Page',
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
        # FIXME: this generates an error the first time it runs, probably due to an error in how we are deleting
        # the initial welcome page.
        root_page.add_child(instance=landing_page)
        return landing_page

    def handle(self, *args, **options):
        index_page = self.create_home_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'], root_page=index_page)
        self.create_social_apps()
