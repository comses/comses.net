"""
Initialize Wagtail Models and other canned data.
"""

import logging
import pathlib

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site as DjangoSite
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from wagtail.wagtailcore.models import Page, Site
from wagtail.wagtailimages.models import Image

from drupal_migrator.utils import get_canonical_image
from home.models import (LandingPage, FeaturedContentItem, SocialMediaSettings,
                         PlatformsIndexPage, Platform, PlatformSnippetPlacement, ResourcesIndexPage, CommunityIndexPage,
                         CategoryIndexPage, CategoryIndexNavigationLink, CategoryIndexItem)
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

    def create_site(self, site_name, hostname):
        # FIXME: appears to be needed for signal handling despite docs that state it shouldn't be necessary
        # revisit and remove at some point if due to misconfiguration
        from django.apps import apps
        apps.get_app_config('home').ready()
        site = Site.objects.first() if Site.objects.count() > 0 else Site()
        site.site_name = site_name
        site.hostname = hostname
        site.is_default_site = True
        site.root_page = self.landing_page
        site.save()
        sms = SocialMediaSettings.for_site(site)
        sms.youtube_url = 'https://www.youtube.com/user/CoMSESNet/'
        sms.twitter_account = 'openabm_comses'
        sms.mailing_list_url = 'http://eepurl.com/b8GCUv'
        sms.save()
        self.site = site

    def create_landing_page(self):
        root_page = Page.objects.get(path='0001')
        # delete root page's initial children.
        root_page.get_children().delete()
        LandingPage.objects.delete()
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
        self.landing_page = landing_page

    def create_resources_section(self):
        resources_index = ResourcesIndexPage(
            title='Resources',
            slug='resources',
            summary=('CoMSES Net is dedicated to fostering open and reproducible computational modeling through '
                     'cyberinfrastructure and community development. We maintain these community curated resources '
                     'to help new and experienced computational modelers improve the discoverability, reuse, and '
                     'reproducibility of our computational models. Feel free to [contact us](/contact/) if you have any'
                     'resources to add or comments.'
                     )
        )
        self.landing_page.add_child(instance=resources_index)
        platforms_index_page = PlatformsIndexPage(title='Computational Modeling Platforms', slug='modeling-platforms')
        for platform in Platform.objects.all().order_by('-name'):
            platforms_index_page.platform_placements.add(
                PlatformSnippetPlacement(platform=platform)
            )
        resources_index.add_child(instance=platforms_index_page)

    def create_community_section(self):
        community_index = CommunityIndexPage(
            title='Welcome to the CoMSES Net Community',
            slug='community',
            summary='''CoMSES Net is dedicated to fostering open and reproducible scientific computation through cyberinfrastructure
            and community development. We are curating a growing collection of resources for model-based science including
            tutorials and FAQ's on agent-based modeling, a computational model library to help researchers archive their
            work and discover and reuse other's works, and forums for discussions, job postings, and events.
            '''
        )
        self.landing_page.add_child(instance=community_index)

    def create_about_section(self):
        about_index = CategoryIndexPage(
            heading='About',
            title='About CoMSES Net / OpenABM',
            slug='about',
            summary='''Welcome! CoMSES Net, the Network for Computational Modeling in Social and Ecological Sciences, is an open
            community of researchers, educators, and professionals with a common goal - improving the way we develop,
            share, use, and re-use agent based and computational models for the study of social and ecological systems.

            CoMSES Net joins the NSF West Big Data Innovation Hub as a spoke in NSF's new national Big Data network and
            is dedicated to fostering open and reproducible scientific computation through cyberinfrastructure and
            community development.
            '''
        )
        for idx, (name, url) in enumerate([('Overview', '/about/'), ('People', '/people/'), ('FAQs', '/faq/'), ('Contact', '/contact/')]):
            about_index.navigation_links.add(
                CategoryIndexNavigationLink(title=name, url=url, sort_order=idx)
            )

        alee = User.objects.get(username='alee')

        preservation_image = get_canonical_image(path='core/static/images/icons/digital-archive.png',
                                                 title='Provide trusted digital preservation and curation',
                                                 user=alee)
        about_index.callouts.add(
            CategoryIndexItem(
                title='Provide trusted digital preservation and curation',
                sort_order=1,
                caption='''You cannot reuse or reproduce that which you cannot find or understand due to lack of context
                and metadata.''',
                image=preservation_image,
            )
        )

        promote_image = get_canonical_image(path='core/static/images/icons/culture.png',
                                            title='Promote a culture of sharing',
                                            user=alee)
        about_index.callouts.add(
            CategoryIndexItem(
                title='Promote a Culture of Sharing, Reuse, and Credit',
                sort_order=2,
                caption='''Publish or perish. Share or shrivel.''',
                image=promote_image
            )
        )

        theory_image = get_canonical_image(path='core/static/images/icons/cog.png',
                                           title='Improve theoretical and methodological practice',
                                           user=alee)
        about_index.callouts.add(
            CategoryIndexItem(
                title='Improve theoretical and methodological practice',
                sort_order=3,
                caption='''Engaging with practitioners to address theoretical concerns and improve methodological practices for
                reuse and reusability.''',
                image=theory_image
            )
        )
        self.landing_page.add_child(instance=about_index)

    def handle(self, *args, **options):
        self.create_landing_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'])
        self.create_social_apps()
        # create community, about, resources pages
        self.create_community_section()
        self.create_resources_section()
        self.create_about_section()
