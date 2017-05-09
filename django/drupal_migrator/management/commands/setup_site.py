"""
Initializes Wagtail Page Models and other canned data. 
FIXME: move logic to dedicated module if this gets too unwieldy
"""

import logging

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site as DjangoSite
from django.core.management.base import BaseCommand
from django.urls import reverse
from wagtail.wagtailcore.models import Page, Site

from home.models import (LandingPage, FeaturedContentItem, SocialMediaSettings,
                         PlatformsIndexPage, Platform, PlatformSnippetPlacement, CategoryIndexPage, StreamPage)
from library.models import Codebase
from drupal_migrator.database_migration import load_licenses, load_platforms

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site = None
        self.landing_page = None
        self.default_user = User.objects.get(username='alee')

    def add_arguments(self, parser):
        parser.add_argument('--site-name',
                            default='CoMSES Net',
                            help='Site human readable name, e.g., Network for Computational ...')
        parser.add_argument('--site-domain',
                            default='www.comses.net',
                            help='Site domain name, e.g., www.comses.net')
        parser.add_argument('--reload-platforms', default=False, action='store_true')
        parser.add_argument('--reload-licenses', default=False, action='store_true')

    def handle(self, *args, **options):
        if options['reload_platforms']:
            load_platforms()
        if options['reload_licenses']:
            load_licenses()

        self.create_landing_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'])
        self.create_social_apps()
        # create community, about, resources pages
        self.create_community_section()
        self.create_resources_section()
        self.create_about_section()

    @staticmethod
    def create_social_apps():
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
        resources_index = CategoryIndexPage(
            heading='Resources',
            title='CoMSES Net Resources',
            slug='resources',
            summary=('CoMSES Net is dedicated to fostering open and reproducible computational modeling through '
                     'cyberinfrastructure and community development. We maintain these community curated resources '
                     'to help new and experienced computational modelers improve the discoverability, reuse, and '
                     'reproducibility of their computational models. Please [contact us](/contact/) with '
                     'feedback or additional resources - your contributions are appreciated!'
                     )
        )
        resources_index.add_breadcrumbs([
            ('Our Resources', '/resources/')
        ])
        resources_index.add_navigation_links([
            ('Resources', '/resources/'),
            ('Modeling Platforms', 'modeling-platforms/'),
            ('Journals', 'journals/'),
            ('Standards', 'standards/'),
        ])
        resources_index.add_callout(
            image_path='core/static/images/icons/modeling-platforms.png',
            title='Modeling Platforms',
            url='modeling-platforms/',
            user=self.default_user,
            sort_order=1,
            caption=('Preserve the complete digital pipeline used to derive a publishable finding. Other researchers '
                     'will be able to discover, cite, and run your code in a reproducible containerized environment.')
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/journals.png',
            title='Scholarly Journals',
            url='journals/',
            caption=('A community curated list of scholarly journals covering a wide range methodological and '
                     'theoretical concerns for agent-based other types of computational modeling.'),
            user=self.default_user,
            sort_order=1,
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/standards.png',
            title='Documentation Standards',
            url='standards/',
            caption=('Advancing the use of agent-based models in scholarly research demands rigorous standards in model '
                     'and experiment documentation. Volker Grimm et al. have developed a protocol for describing '
                     'agent-based and individual-based models called '
                     '[ODD (Overview, Design Concepts, and Details)](https://doi.org/10.1016/j.ecolmodel.2010.08.019) '
                     '"designed to ensure that such descriptions are readable and complete."'
                     ),
            user=self.default_user,
            sort_order=2,
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/educational-materials.png',
            title='Educational Materials',
            url='educational-materials/',
            caption=('Tutorials, websites, books, and classroom / course materials on agent-based modeling that cover '
                     'various modeling platforms (e.g., RePast, NetLogo, Mason, FLAME).'),
            user=self.default_user,
            sort_order=3,
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/guides-to-good-practice.png',
            title='Guides to Good Practice',
            url='guides-to-good-practice/',
            caption=('Good practices for agent-based modeling as inspired by '
                     '[this Software Carpentry paper](https://swcarpentry.github.io/good-enough-practices-in-scientific-computing/)'),
            user=self.default_user,
            sort_order=4,
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/events.png',
            url=reverse('home:event-list'),
            title='Find Upcoming Events',
            caption=('Find calls for papers and participation in upcoming conferences, workshops, and other events '
                     'curated by the CoMSES Net Community.'),
            user=self.default_user,
            sort_order=5,
        )
        self.landing_page.add_child(instance=resources_index)
        platforms_index_page = PlatformsIndexPage(title='Computational Modeling Platforms', slug='modeling-platforms')
        for platform in Platform.objects.all().order_by('-name'):
            platforms_index_page.platform_placements.add(
                PlatformSnippetPlacement(platform=platform)
            )
        resources_index.add_child(instance=platforms_index_page)

    def create_community_section(self):
        community_index = CategoryIndexPage(
            heading='Community',
            title='Welcome to the CoMSES Net Community',
            slug='community',
            summary='''CoMSES Net is dedicated to fostering open and reproducible scientific computation through cyberinfrastructure
            and community development. We are curating a growing collection of resources for model-based science including
            tutorials and FAQ's on agent-based modeling, a computational model library to help researchers archive their
            work and discover and reuse other's works, and forums for discussions, job postings, and events.
            '''
        )
        community_index.add_breadcrumbs([
            ('Community', '/community/')
        ])
        community_index.add_navigation_links([
            ('Community', '/community/'),
            ('Forum', settings.DISCOURSE_BASE_URL),
            ('Users', reverse('home:profile-list')),
            ('Jobs', reverse('home:job-list')),
        ])
        # add callouts
        community_index.add_callout(
            image_path='core/static/images/icons/connect.png',
            title='Connect with Researchers',
            user=self.default_user,
            sort_order=1,
            caption=('Follow other researchers, their models, or other topics of interest. Engage in discussions, '
                     'participate in upcoming events, or find a new job. Preserve the complete digital pipeline used to '
                     'derive a publishable finding. Other researchers will be able to discover, cite, and run your code '
                     'in a reproducible' 'containerized environment.')
        )

        community_index.add_callout(
            image_path='core/static/images/icons/events.png',
            title='Find Upcoming Events',
            url=reverse('home:event-list'),
            user=self.default_user,
            sort_order=2,
            caption=('Find calls for papers and participation in upcoming conferences, workshops, and other events '
                     'curated by the CoMSES Net Community.'),
        )

        community_index.add_callout(
            image_path='core/static/images/icons/jobs.png',
            title='Search Jobs & Appointments',
            url=reverse('home:job-list'),
            user=self.default_user,
            sort_order=3,
            caption=('We maintain an open job board with academic and industry positions relevant to the CoMSES Net '
                     'Community. Any CoMSES Net Member can register and post positions here.')
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
            We have been developing a computational model library to preserve the digital artifacts and source code that
            comprise an agent based model and encourage you to register and
            [add your models to the archive](/codebases/create/). We are governed by an international board and ex-officio
            members (PIs of the projects that fund CoMSES Net) and operate under [these by-laws](/about/by-laws). 
            '''
        )
        about_index.add_breadcrumbs([('About CoMSES Net', '/about/')])
        about_index.add_navigation_links([('Overview', '/about/'),
                                          ('People', 'people/'),
                                          ('FAQs', '/faq/'),
                                          ('Contact', '/contact/')])
        about_index.add_callout(
            image_path='core/static/images/icons/digital-archive.png',
            title='Provide trusted digital preservation and curation',
            user=self.default_user,
            sort_order=1,
            caption='Facilitate reuse and reproducibility with rich contextual metadata.'
        )
        about_index.add_callout(
            image_path='core/static/images/icons/culture.png',
            title='Promote a culture of sharing',
            user=self.default_user,
            sort_order=2,
            caption='Publish or perish. Share or shrivel.',
        )
        about_index.add_callout(
            image_path='core/static/images/icons/cog.png',
            title='Improve theoretical and methodological practice',
            user=self.default_user,
            sort_order=3,
            caption='''Engage with practitioners to address theoretical concerns and improve methodological practices 
            for reuse and reusability.''',
        )
        self.landing_page.add_child(instance=about_index)
        people_page = StreamPage(
            title='People',
            description='''The CoMSES Net Directorate is led by Michael Barton, Marco Janssen, Allen Lee, 
                        and Lilian Na'ia Alessa. It also includes an executive board elected by and from full CoMSES 
                        Net members and a support staff with expertise in digital curation and cyberinfrastructure
                        development.'''
        )
        about_index.add_child(instance=people_page)
