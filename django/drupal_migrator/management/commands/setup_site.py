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

from drupal_migrator.database_migration import load_licenses, load_platforms, load_journals, load_faq_entries
from home.models import (LandingPage, FeaturedContentItem, PlatformIndexPage, PlatformSnippetPlacement,
                         CategoryIndexPage, JournalIndexPage,
                         JournalSnippetPlacement, Journal, MarkdownPage, FaqPage, FaqEntry, FaqEntryPlacement,
                         PeoplePage, PeopleEntryPlacement, ContactPage)
from core.models import SocialMediaSettings, Platform
from library.models import Codebase

logger = logging.getLogger(__name__)


class AbstractSection(object):

    def __init__(self, root_page, default_user):
        self.root_page = root_page
        self.default_user = default_user


class ResourceSection(AbstractSection):

    SUBNAVIGATION_LINKS = (
        ('Resources', '/resources/'),
        ('Modeling Platforms', '/resources/modeling-platforms/'),
        ('Journals', '/resources/journals/'),
        ('Standards', '/resources/standards/'),
    )

    def build_resource_index(self):
        resources_index = CategoryIndexPage(
            heading='Resources',
            title='CoMSES Net Resources',
            slug='resources',
            summary=('CoMSES Net is dedicated to fostering open and reproducible computational modeling through '
                     'cyberinfrastructure and community development. We maintain these community curated resources '
                     'to help new and experienced computational modelers improve the discoverability, reuse, and '
                     'reproducibility of their computational models. Please [contact us](/contact/) with '
                     'feedback or additional resources - your contributions are appreciated!'
                     '\n'
                     '### Other Web Resources\n'
                     '[Leigh Tesfatsion](http://www2.econ.iastate.edu/tesfatsi/) also maintains an '
                     '[online guide for newcomers to agent-based modeling in the social sciences]'
                     '(http://www2.econ.iastate.edu/tesfatsi/abmread.htm) with many useful links.'
                     )
        )
        # FIXME: replace with wagtailmenus FlatMenu creation and associated with the resources_index
        resources_index.add_breadcrumbs(self.SUBNAVIGATION_LINKS[:1])
        resources_index.add_navigation_links(self.SUBNAVIGATION_LINKS)
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
            caption=(
                'Advancing the use of agent-based models in scholarly research demands rigorous standards in model '
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
        self.root_page.add_child(instance=resources_index)
        return resources_index

    def build_platforms_index(self, parent_page):
        platforms_index_page = PlatformIndexPage(
            title='Computational Modeling Platforms',
            slug='modeling-platforms',
            description=("Computational modeling platforms provide a wide range of modeling strategies, scaffolding, "
                         "and support for developers of agent-based models. Please [let us know](/contact/) if you "
                         "have any corrections or would like to submit a new platform.")
        )
        platforms_index_page.add_breadcrumbs(self.SUBNAVIGATION_LINKS[:2])
        platforms_index_page.add_navigation_links(self.SUBNAVIGATION_LINKS)
        for idx, platform in enumerate(Platform.objects.exclude(name='other').order_by('name')):
            platforms_index_page.platform_placements.add(
                PlatformSnippetPlacement(sort_order=idx, platform=platform)
            )
        parent_page.add_child(instance=platforms_index_page)

    def build_journal_page(self, parent):
        journal_page = JournalIndexPage(
            slug='journals',
            title='Computational Modeling Journals',
            description=('A list of scholarly journals that address theoretical and methodological concerns for '
                         'agent-based modeling and related computational modeling sciences. To submit any corrections '
                         'or add a new journal, please [contact us](/contact/).'
                         ),
        )
        # FIXME: arcane step value slice to pick out Resources -> Journals
        journal_page.add_breadcrumbs(self.SUBNAVIGATION_LINKS[0:3:2])
        journal_page.add_navigation_links(self.SUBNAVIGATION_LINKS)

        for idx, journal in enumerate(Journal.objects.order_by('name')):
            journal_page.journal_placements.add(
                JournalSnippetPlacement(sort_order=idx, journal=journal)
            )
        parent.add_child(instance=journal_page)

    def build_standards_page(self, parent):
        standards_page = MarkdownPage(
            heading='Resources',
            slug='standards',
            title='Documentation Standards',
            description=(
                'Advancing the use of agent-based models in scholarly research demands rigorous standards in model '
                'code and experiment documentation. CoMSES Net supports open metadata and documentation standards '
                'including [codemeta](https://github.com/codemeta/codemeta), [DataCite](https://www.datacite.org/), '
                'and the [ODD protocol](https://doi.org/10.1016/j.ecolmodel.2010.08.019).'
            ),
            body=('[The ODD Protocol](http://www.ufz.de/index.php?de=40429) was initially proposed by Volker Grimm '
                  'et al. in 2006 with the following rationale: \n\n'
                  '> Simulation models that describe autonomous individual organisms (individual based models, IBM) or '
                  'agents (agent-based models, ABM) have become a widely used tool, not only in ecology, but also in '
                  'many other disciplines dealing with complex systems made up of autonomous entities. However, there '
                  'is no standard protocol for describing such simulation models, which can make them difficult to '
                  'understand and to duplicate. '
                  '<footer class="blockquote-footer">[(Grimm, V. et al., 2006, p.115)]'
                  '(https://doi.org/10.1016/j.ecolmodel.2006.04.023)</footer> \n\n'
                  'The ODD is organized around the three main components to be documented about a model: \n\n'
                  '1. Overview\n'
                  '2. Design concepts \n'
                  '3. Details \n\n'
                  'These components encompass seven sub-elements that must be documented in sufficient depth for the '
                  'model&apos;s purpose and design to be clear and replicable for a third party: *Purpose, '
                  'State Variables and Scales, Process Overview and Scheduling, Design Concepts, Initialization, '
                  'Input, and Submodels*. \n\n'
                  'In addition to the original 2006 publication, Grimm et al. have continued to publish updates '
                  'to the protocol with examples of its application to research projects.\n\n'
                  '- [The ODD Protocol: a review and first update](http://dx.doi.org/10.1016/j.ecolmodel.2010.08.019)\n'
                  '- [Using the ODD Protocol for Describing Three Agent-Based Social Simulation Models of '
                  'Land-Use Change](http://jasss.soc.surrey.ac.uk/11/2/3.html)'
                  )
        )
        standards_page.add_breadcrumbs(self.SUBNAVIGATION_LINKS[0:4:3])
        standards_page.add_navigation_links(self.SUBNAVIGATION_LINKS)
        parent.add_child(instance=standards_page)

    def build(self):
        resources_index = self.build_resource_index()
        self.build_platforms_index(resources_index)
        self.build_journal_page(resources_index)
        self.build_standards_page(resources_index)


class CommunitySection(AbstractSection):

    def build_community_index(self):
        community_index = CategoryIndexPage(
            heading='Community',
            title='Welcome to the CoMSES Net Community',
            slug='community',
            summary=('CoMSES Net is dedicated to fostering open and reproducible scientific computation through '
                     'cyberinfrastructure and community development. We curate [resources for '
                     'model-based science](/resources/) including tutorials and FAQs on agent-based modeling, a '
                     '[computational model library](/codebases/) to help researchers archive their work and discover '
                     'and reuse other&apos;s works, and '
                     '[forums for discussions, job postings, and events.](https://forum.comses.net)'
                     ),
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
            url=reverse('home:profile-list'),
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
        self.root_page.add_child(instance=community_index)

    def build(self):
        self.build_community_index()


class AboutSection(AbstractSection):
    SUBNAVIGATION_MENU = [('About', '/about/'),
                          ('People', '/about/people/'),
                          ('FAQs', '/about/faq/'),
                          ('Contact', '/about/contact/')]

    def build_about_section(self):
        about_index = CategoryIndexPage(
            heading='About',
            title='About CoMSES Net / OpenABM',
            slug='about',
            summary=('Welcome! CoMSES Net, the Network for Computational Modeling in Social and Ecological Sciences, '
                     'is an open community of researchers, educators, and professionals with a common goal - improving '
                     'the way we develop, share, use, and re-use agent based and computational models for the study of '
                     'social and ecological systems. We have been developing a computational model library to preserve '
                     'the digital artifacts and source code that comprise an agent based model and encourage you to '
                     'register and [add your models to the archive](/codebases/create/). We are governed by an '
                     'international board and ex-officio members (PIs of the projects that fund CoMSES Net) and '
                     'operate under [these by-laws](/about/by-laws).'
                     ),
        )
        about_index.add_breadcrumbs(self.SUBNAVIGATION_MENU[:1])
        about_index.add_navigation_links(self.SUBNAVIGATION_MENU)
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
            caption=('Engage with practitioners to address theoretical concerns and improve methodological practices '
                     'for reuse and reusability.'),
        )
        self.root_page.add_child(instance=about_index)
        return about_index

    def build_people_page(self, parent):
        people_page = PeoplePage(
            title='People',
            heading='About',
            description=("The CoMSES Net Directorate is led by [Michael Barton](/users/cmbarton/), "
                         "[Marco Janssen](/users/marcojanssen/), [Lilian Na'ia Alessa](/users/lil.alessa/), "
                         "[Allen Lee](/users/alee/), and Ken Buetow in consultation with an executive board elected by "
                         "full CoMSES Net members and a dedicated support staff with expertise in digital curation and "
                         "community cyberinfrastructure development."
                         ),
        )
        directorate = ('cmbarton', 'marcojanssen', 'lil.alessa', 'alee')
        offset = 0
        people_page.add_users(category=PeopleEntryPlacement.CATEGORIES.directorate,
                              usernames=directorate,
                              offset=offset)
        offset += len(directorate)
        board = ('fstonedahl', 'mzellner', 'clepage', 'wrand', 'mariam.kiran', 'garypolhill', 'abell')
        people_page.add_users(category=PeopleEntryPlacement.CATEGORIES.board,
                              usernames=board,
                              offset=offset)
        offset += len(board)
        people_page.add_users(PeopleEntryPlacement.CATEGORIES.digest,
                              usernames=('john.t.murphy',),
                              offset=offset)
        offset += 1
        staff = ('cpritcha',)
        people_page.add_users(category=PeopleEntryPlacement.CATEGORIES.staff,
                              usernames=staff,
                              offset=offset)
        offset += len(staff)

        alumni = ('volker.grimm@ufz.de', 'bruceedmonds')
        people_page.add_users(category=PeopleEntryPlacement.CATEGORIES.alumni,
                              usernames=alumni,
                              offset=offset)
        people_page.add_breadcrumbs(self.SUBNAVIGATION_MENU[0:2])
        people_page.add_navigation_links(self.SUBNAVIGATION_MENU)
        parent.add_child(instance=people_page)

    def build_faq_page(self, parent):
        faq_page = FaqPage(
            slug='faq',
            title='Frequently Asked Questions',
            description=('We have organized our frequently asked questions into categories to make it easier to find '
                         "answers.\n\nIf you have a question that is not answered here, you can "
                         "[register](/accounts/signup/) as a CoMSES Net Member and post it to our forums. With "
                         "enough community interest, it may end up on this list."),
        )
        faq_page.add_breadcrumbs(self.SUBNAVIGATION_MENU[0:3:2])
        faq_page.add_navigation_links(self.SUBNAVIGATION_MENU)
        for idx, faq_entry in enumerate(FaqEntry.objects.order_by('id')):
            faq_page.faq_entry_placements.add(
                FaqEntryPlacement(sort_order=idx, faq_entry=faq_entry)
            )
        parent.add_child(instance=faq_page)

    def build_contact_page(self, parent):
        contact_page = ContactPage(
            slug='contact',
            title='Contact Us',
            description=('Please use this form to contact us if you have any concerns, feedback, or corrections. '
                         'Thanks!')
        )
        contact_page.add_breadcrumbs(self.SUBNAVIGATION_MENU[0:4:3])
        contact_page.add_navigation_links(self.SUBNAVIGATION_MENU)
        parent.add_child(instance=contact_page)


    def build(self):
        about_index = self.build_about_section()
        self.build_people_page(about_index)
        self.build_faq_page(about_index)
        self.build_contact_page(about_index)


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
        parser.add_argument('--reload-journals', default=False, action='store_true')
        parser.add_argument('--reload-faq', default=False, action='store_true')

    def handle(self, *args, **options):
        if options['reload_platforms']:
            load_platforms()
        if options['reload_licenses']:
            load_licenses()
        if options['reload_journals']:
            load_journals()
        if options['reload_faq']:
            load_faq_entries()

        self.create_landing_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'])
        self.create_social_apps()
        # create community, about, resources pages
        for section in (CommunitySection, ResourceSection, AboutSection):
            section(self.landing_page, self.default_user).build()

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
        sms.contact_form_recipients = 'editors@openabm.org'
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
            mission_statement=('CoMSES Net is an international network of researchers, educators and professionals '
                               'with the common goal of improving the way we develop, share, and use agent based '
                               'modeling in the social and ecological sciences.'
                               ),
            community_statement=(
                "CoMSES Net is dedicated to fostering open and reproducible scientific computation through "
                "cyberinfrastructure and community development. We curate resources for model-based science "
                "including tutorials and FAQs on agent-based modeling, a [computational model library](/codebases) "
                "where researchers can archive their work and discover and reuse other's works, and open access forums "
                "for job postings, events, and discussion. \n\n"
                'As a scientific community of practice, members of the CoMSES Network have access to a suite of '
                'community resources and also share a responsibility to contribute back to the community.'
            ),
        )
        for codebase in Codebase.objects.peer_reviewed():
            # if there are multiple images, just pull the first
            fc_dict = codebase.as_featured_content_dict()
            if fc_dict['image']:
                landing_page.featured_content_queue.add(FeaturedContentItem(**fc_dict))
        # refresh from DB before adding more nodes so treebeard can clean up its internals
        # https://django-treebeard.readthedocs.io/en/latest/caveats.html
        root_page.refresh_from_db()
        root_page.add_child(instance=landing_page)
        self.landing_page = landing_page
