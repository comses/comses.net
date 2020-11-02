"""
Initializes Wagtail Page Models and other canned data.
FIXME: refactor, this is getting too bigly
"""

import logging

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site as DjangoSite
from django.core.management.base import BaseCommand
from django.urls import reverse
from wagtail.wagtailcore.models import Page, Site

from core.models import SocialMediaSettings, Platform
from drupal_migrator.database_migration import load_licenses, load_platforms, load_journals, load_faq_entries
from home.models import (LandingPage, FeaturedContentItem, PlatformIndexPage, PlatformSnippetPlacement,
                         CategoryIndexPage, JournalIndexPage, JournalSnippetPlacement, Journal,
                         MarkdownPage, FaqPage, FaqEntry, FaqEntryPlacement,
                         PeoplePage, PeopleEntryPlacement, ContactPage)
from library.models import Codebase

logger = logging.getLogger(__name__)


COMMUNITY_STATEMENT = (
    'CoMSES Net is dedicated to fostering open and reproducible scientific computation through '
    'cyberinfrastructure and community development. We develop and curate [resources for model-based '
    'science](/resources/) including agent-based modeling [tutorials](/resources/tutorials/), [FAQs](/about/faq/), '
    'and [forums for discussions, job postings, and events.](https://forum.comses.net). We also develop and '
    'maintain the [OpenABM Computational Model Library](/codebases/), a digital repository for code that supports '
    'discovery and good practices for software citation, reproducibility and reuse.'
    '- [OpenABM Computational Model Library](/codebases/)'
    '- [Resources for model-based science](/resources/)'
    '- [FAQs for agent-based modeling](/about/faq/)'
    '- [Guides to good practice](resources/guides-to-good-practice/)'
    '- [Discussion Forums](https://forum.comses.net)'
    '- [A Job Board](https://forum.comses.net/c/jobs-and-appointments/)'
    '- [Events Calendar](https://www.comses.net/events/)'
    '- And [YouTube channel](https://www.youtube.com/user/CoMSESNet/playlists) with video playlists related to agent-based modeling and archived videos from our virtual conferences.'
)

class AbstractSection(object):

    def __init__(self, root_page, default_user):
        self.root_page = root_page
        self.default_user = default_user


class ResourceSection(AbstractSection):

    SUBNAVIGATION_LINKS = (
        ('Resources', '/resources/'),
        ('Platforms', '/resources/modeling-platforms/'),
        ('Journals', '/resources/journals/'),
        ('Standards', '/resources/standards/'),
        ('Education', '/resources/education/'),

    )

    def build_resource_index(self):
        resources_index = CategoryIndexPage(
            heading='Resources',
            title='CoMSES Net Resources',
            slug='resources',
            summary=('CoMSES Net is dedicated to fostering open and reproducible computational modeling through '
                     'cyberinfrastructure and community development. We maintain these community curated resources '
                     'to help new and experienced computational modelers improve the discoverability, reuse, and '
                     'reproducibility of their computational models. Please [contact us](/about/contact/) with '
                     'feedback or additional resources - your contributions are appreciated!'
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
            caption=(
                'Preserve the complete digital pipeline used to derive a publishable finding in a trusted digital '
                'repository that supports discovery and good practices for software citation, reproducibility, and '
                'reuse.'
            ),
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
            title='Education',
            url='education/',
            caption=('Tutorials, websites, books, and classroom / course materials on agent-based modeling that cover '
                     'various modeling platforms (e.g., RePast, NetLogo, Mason, FLAME).'),
            user=self.default_user,
            sort_order=3,
        )
        resources_index.add_callout(
            image_path='core/static/images/icons/guides-to-good-practice.png',
            title='Guides to Good Practice',
            url='guides-to-good-practice/',
            caption=('Good practices for agent-based modeling and software development ala '
                     '[the Software and Data Carpentry organizations](http://carpentries.org/) and '
                     '[*Good Enough Practices in Scientific Computing*]'
                     '(https://swcarpentry.github.io/good-enough-practices-in-scientific-computing/).'),
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
                         "and support for developers of agent-based models. Please [let us know](/about/contact/) if you "
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
                         'or add a new journal, please [contact us](/about/contact/).'
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
                  '- [The ODD Protocol: a review and first update](https://doi.org/10.1016/j.ecolmodel.2010.08.019)\n'
                  '- [Using the ODD Protocol for Describing Three Agent-Based Social Simulation Models of '
                  'Land-Use Change](http://jasss.soc.surrey.ac.uk/11/2/3.html)'
                  )
        )
        standards_page.add_breadcrumbs(self.SUBNAVIGATION_LINKS[0:4:3])
        standards_page.add_navigation_links(self.SUBNAVIGATION_LINKS)
        parent.add_child(instance=standards_page)

    def build_education_page(self, parent):
        education_page = MarkdownPage(
            heading='Resources',
            slug='education',
            title='Educational Materials',
            description=(
                'A collection of tutorials, classroom / course materials, and educational content on agent '
                'based and computational modeling. If you have anything to add to this list, please '
                '[let us know](/about/contact/).'
            ),
            body=('## Books and other resources\n\n'
                  '* [Agent-based and Individual-based Modeling: *A Practical Introduction* by Steven F. Railsback and Volker Grimm]'
                  '(http://www.railsback-grimm-abm-book.com/) - A textbook on applying agent-based models to study complex systems, '
                  'intended for upper-level undergraduates, graduate students, or self-instruction. \n'
                  '* [Introduction to Agent-Based Modeling by Marco Janssen](https://www.gitbook.com/book/cbie/introduction-to-agent-based-modeling)'
                  ' - An introductory undergraduate course on agent based modeling.\n'
                  '* [Guide for Newcomers to Agent-Based Modeling in the Social Sciences by Robert Axelrod and Leigh Tesfatsion]'
                  '(http://www2.econ.iastate.edu/tesfatsi/abmread.htm)\n'
                  '* [CSDMS Educational Repository](http://csdms.colorado.edu/wiki/Education_portal) - the [Community '
                  'Surface Dynamics Modeling System (CSDMS)](http://csdms.colorado.edu/wiki/About_CSDMS) is a diverse community of '
                  'experts promoting good practices for the modeling of earth surface processes and surface dynamics models.\n'
                  '* [Software and Data Carpentry](https://carpentries.org/) - the Software and Data Carpentries teach researchers '
                  'foundational computational and data science skills through short, impactful workshops.\n'
                  '* [CoMSES Net YouTube video channel](https://www.youtube.com/user/CoMSESNet)\n'
                  '* [CoMSES Net Frequently Asked Questions on Agent Based Modeling](/about/faq/)\n\n'
                  '## Classroom materials \n\n'
                  '*Links coming soon*\n\n'
                  '* Dawn Parker - "Spatial Agent-based Models of Human-Environment Interactions" \n'
                  '* Bruce Edmonds - "Introduction to Agent-Based Modelling in NetLogo - A 2-Day Course" \n'
                  '* Michael Barton - "Introduccion al Modelar de Agentes para la Arqueología" \n\n'
                  '### [Cormas](http://cormas.cirad.fr/en/outil/outil.htm)\n\n'
                  '> Cormas is a simulation platform based on the VisualWorks programming environment and SmallTalk.\n\n'
                  '* [Cormas tutorials](http://cormas.cirad.fr/en/outil/classroom/)\n'
                  '### [MASON](https://cs.gmu.edu/~eclab/projects/mason/)\n\n'
                  '> MASON is a fast discrete-event multiagent simulation library core in Java, designed to be the foundation for large custom-purpose '
                  'Java simulations, and also to provide more than enough functionality for many lightweight simulation needs. MASON contains both a '
                  'model library and an optional suite of visualization tools in 2D and 3D.\n\n'
                  '* [Online docs](https://cs.gmu.edu/~eclab/projects/mason/docs/)\n'
                  '* [PDF Manual](https://cs.gmu.edu/~eclab/projects/mason/manual.pdf)\n\n'
                  '### [NetLogo](http://ccl.northwestern.edu/netlogo/)\n\n'
                  '> NetLogo is a free multi-agent programmable modeling environment originally authored by Uri Wilensky and developed at the '
                  '[Center for Connected Learning and Computer-Based Modeling](http://ccl.northwestern.edu/).\n\n'
                  '* [Official documentation: http://ccl.northwestern.edu/netlogo/docs/](http://ccl.northwestern.edu/netlogo/docs/)\n'
                  '* [NetLogo Development Team Tutorial: Models](http://ccl.northwestern.edu/netlogo/docs/tutorial1.html)\n'
                  '* [NetLogo Development Team Tutorial: Commands](http://ccl.northwestern.edu/netlogo/docs/tutorial2.html)\n'
                  '* [NetLogo Development Team Tutorial: Procedures](http://ccl.northwestern.edu/netlogo/docs/tutorial3.html)\n'
                  '* [NetLogo 6.0 Quick Guide by Luis Izquierdo](http://luis.izqui.org/resources/NetLogo-6-0-QuickGuide.pdf) - a printable reference sheet\n'
                  '* [Introduction to NetLogo by René Doursat](http://doursat.free.fr/docs/CS790R_S05/CS790R_S05_Lecture_4_NetLogo.pdf)\n'
                  '* [Additional Resources](http://ccl.northwestern.edu/netlogo/resources.shtml) - a collection of links from the NetLogo development team\n'
                  '* [Manual de NetLogo en español](http://sites.google.com/site/manualnetlogo/) - Un manual de Netlogo en español que te permitirá '
                  'familiarizarte con este lenguaje de programación de una forma muy sencilla, a través de pequeños programas-ejemplo.\n\n'
                  '### [RePast](https://repast.github.io/index.html)\n\n'
                  '> The Repast Suite is a family of advanced, free, and open source agent-based modeling and simulation platforms that have collectively '
                  'been under continuous development for over 15 years.\n\n'
                  '* [Official documentation: https://repast.github.io/docs.html](https://repast.github.io/docs.html)\n'
                  '* [Repast 3 tutorials](http://repast.sourceforge.net/repast_3/tutorials.html)\n'
                  '* [RepastHPC Tutorial](https://repast.github.io/hpc_tutorial/TOC.html)\n\n'
                  )
        )
        education_page.add_breadcrumbs(self.SUBNAVIGATION_LINKS[0:5:4])
        education_page.add_navigation_links(self.SUBNAVIGATION_LINKS)
        parent.add_child(instance=education_page)

    def build_good_practice_page(self, parent):
        page = MarkdownPage(
            heading='Resources',
            slug='guides-to-good-practice',
            title='Guides to Good Practice',
            description=(
                'We strive to foster and support good practices for developing and disseminating open and reproducible '
                'computational models. Computational modeling is not a primary skill for most practitioners but instead a '
                'tool that we can use to better understand the emergent phenomena that arise from the complex adaptive '
                'systems that we engage in every day. If you are interested in improving foundational computational and '
                'data science skills, check out [the Software and Data Carpentries organizations](http://carpentries.org) '
                'and look for an [upcoming workshop](https://software-carpentry.org/workshops/) near you.'
            ),
            body=(
                '### Agent-based model development \n\n'
                '* Keep your models simple\n'
                '* Document your models using ODD or equivalent documentation protocol\n'
                '* Perform sensitivity analysis on your model variables\n\n\n'
                'Some of the code and data management practices listed below are also described in greater detail in '
                '[*Good Enough Practices in Scientific Computing* by Wilson et al]'
                '(https://swcarpentry.github.io/good-enough-practices-in-scientific-computing/).'
                ' It is definitely worth a read if you would like to further explore these topics. \n'
                '### Code management \n\n'
                '* Use a version control system\n'
                '* Document all external dependencies (e.g., Docker, pip, packrat)\n'
                '* Strive for simple, well-commented, self-documenting code with meaningful variable names\n'
                '* Adopt or develop community documentation standards (e.g., '
                '[ODD](https://doi.org/10.1016/j.ecolmodel.2010.08.019))\n'
                '* Adopt a consistent, self-describing '
                '[directory structure](https://swcarpentry.github.io/good-enough-practices-in-scientific-computing/#project-organization) '
                'for your code, data, documentation, and results\n'
                '* Archive your codebase in a DOI-issuing repository that provides citable URLs for specific '
                'versions of your codebase [(Force11 software citation principles)]'
                '(https://www.force11.org/software-citation-principles) \n'
                '* Provide example test cases and expected outputs\n\n\n'
                '### Data management \n\n'
                '* Preserve raw and intermediate forms of data\n'
                '* Document all data cleaning and processing steps\n'
                '* Script your data analysis as opposed to manually munging an Excel sheet\n'
                '* Archive your data in a DOI-issuing repository that provides citable URLs for specific versions of your dataset\n'
                '* Create [tidy, analysis-friendly data](https://swcarpentry.github.io/good-enough-practices-in-scientific-computing/#data-management)\n'
            ),
        )
        page.add_breadcrumbs([('Resources', '/resources/'), ('Guides to Good Practice', 'good-practices')])
        parent.add_child(instance=page)

    def build(self):
        resources_index = self.build_resource_index()
        self.build_platforms_index(resources_index)
        self.build_journal_page(resources_index)
        self.build_standards_page(resources_index)
        self.build_education_page(resources_index)
        self.build_good_practice_page(resources_index)


class CommunitySection(AbstractSection):

    def build_community_index(self):
        community_index = CategoryIndexPage(
            heading='Community',
            title='Welcome to the CoMSES Net Community',
            slug='community',
            summary=COMMUNITY_STATEMENT,
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
                     'participate in upcoming events, or find a new job. Preserve the complete digital pipeline used '
                     'to derive a publishable finding in a trusted digital repository that supports discovery and '
                     'good practices for software citation, reproducibility, and reuse.'
                     )
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
                     'Community. Any registered CoMSES Net members can post positions here.')
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
                     'social and ecological systems. We develop and maintain the [OpenABM Computational Model Library]('
                     '/codebases/), a digital repository that supports discovery and good practices for '
                     '[software citation](https://www.force11.org/software-citation-principles), digital preservation, '
                     'reproducibility, and reuse. We encourage you to [join CoMSES Net](/accounts/signup) and '
                     '[add your models to the archive](/codebases/create/).\n\n'
                     'We are governed by an international executive board, ex-officio members '
                     '(PIs on projects that fund CoMSES Net) and adhere to '
                     '[these community drafted by-laws](/about/by-laws/).'
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
            description=("CoMSES Net is led by [Michael Barton](/users/5/), [Marco Janssen](/users/4/),"
                         "[Lilian Na'ia Alessa](/users/7/), [Allen Lee](/users/3/), and Ken Buetow in "
                         "consultation with an executive board elected by CoMSES Net members."
                         ),
        )
        directorate = ('cmbarton', 'marcojanssen', 'lil.alessa', 'alee')
        offset = 0
        people_page.add_users(category=PeopleEntryPlacement.CATEGORIES.directorate,
                              usernames=directorate,
                              offset=offset)
        offset += len(directorate)
        board = ('fstonedahl', 'mzellner', 'mariam.kiran', 'abell', 'kgrogers', 'wrand')
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

        alumni = ('volker.grimm@ufz.de', 'bruceedmonds', 'clepage', 'garypolhill', )
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

    def build_bylaws_page(self, parent):
        bylaws_page = MarkdownPage(
            heading='CoMSES Net By-Laws',
            title='CoMSES Net By-Laws',
            description='Community drafted By-Laws for the operation of CoMSES Net.',
            slug='by-laws',
            body=(
                '[TOC]\n\n'
                '# Article I: The Organization \n\n'
                '**A.** This organization shall be known as the Network for Computational Modeling in '
                'the Social and Ecological Sciences (CoMSES Net)\n'
                '**B.** CoMSES Net is a scientific research coordination network to support and expand the development and '
                'use of computational modeling in the social and ecological sciences.\n'
                '**C.** One of the primary nodes of CoMSES Net is OpenABM, which serves specifically as a platform to '
                'promote education and use of agent-based modeling\n'
                '**D.** Toward these ends, the organization will develop actions and projects to further these aims, '
                'including cyberinfrastructure development and maintenance, workshops and winter/summer schools, '
                'foster various mechanisms to promote sharing of research and educational material related to '
                'computational modeling in the social and ecological sciences.\n\n'
                '# Article II: Membership \n\n'
                '**A.** Membership is open to all persons who sign up to this website. Registered users can post materials '
                'to the website. Full members agree to the responsibilities and code of behavior and receive '
                'additional benefits and obligations as specified at the organizational website. \n'
                '**B.** Full members have the right to vote for composition of the executive board and are eligible '
                'to be candidates for the board (See Article III).\n'
                '**C.** Members can be expelled under exceptional conditions for repeated violations of the members rules, '
                'confirmed by a unanimous vote of the Board.\n\n'
                '# Article III: Composition of the Executive Board \n\n'
                '**A.** The board consists of six elected board members and additional ex-officio members '
                '(Principal Investigators on the main projects that fund this organization). Each board member will '
                'generally be responsible for a defined set of tasks related to management of the network. If a '
                'board member is both elected and qualified to serve as an ex officio member they still have only one '
                'vote, but are eligible for any rights which apply to either category of board membership.\n'
                '**B.** The board elects every year an elected member to serve as a chair.\n'
                '**C.** The board advises on the strategy and operations of the organizations beyond the current funded '
                'projects. The board can initiate and direct activities using the existing cyberinfrastructure. '
                'The principal responsibility of funded projects is held by the principal investigators.\n'
                '**D.** The board meets at least three times a year. Meetings need not be in person, but can be by audio '
                'or video teleconference.\n'
                '**E.** Decisions are made by majority vote of the board members.\n'
                '**F.** Board member terms are three years. Each year two board members rotate off the board and new '
                'members will be elected. Any other vacancy (due to resignation, incapability determined by two-thirds '
                'of the board) will be filled by the next annual election.\n\n'
                '# Article IV: Ex-officio Members \n\n'
                '**A.** Principal investigators of official projects supporting the CoMSES Net organization.\n'
                '**B.** Typical support of CoMSES Net includes direct financial support of the organization, '
                'administrative support in-kind or research activities that directly benefit CoMSES Net and its '
                'member organizations.\n'
                '**C.** Any member organization that believes it has met the criteria outlined in IV.A and IV.B can request '
                'to designate an ex-officio member to the board. This request must be approved by a simple majority '
                'of the current board.\n\n'
                '# Article V: Elections \n\n'
                '**A.** All Full CoMSES members are eligible to vote on elected members of the board.\n'
                '**B.** Elections shall take place in November/December of each year. Executive Board terms begin '
                'January 1st.'
            ),
        )
        parent.add_child(instance=bylaws_page)

    def build_orcid_page(self, parent):
        orcid_page = MarkdownPage(
            heading='CoMSES Net & ORCID',
            title='CoMSES Net & ORCID',
            description=(
                '<span class="float-right">![orcid logo](/static/images/logo-orcid-member-170px.png)</span>\n'
                '<i class="ai ai-orcid text-orcid"></i>[ORCID](https://orcid.org) provides a persistent digital identifier that distinguishes you '
                'from other researchers.'
            ),
            slug='orcid',
            body=(
                '## What is ORCID?\n\n'
                'ORCID provides researchers with a unique identifier (an ORCID iD <i class="ai ai-orcid text-orcid"></i>) '
                'plus a mechanism for linking their research outputs and activities to their ORCID iD.\n\n'
                'ORCID is integrated into many systems used by publishers, funders, institutions, and other '
                'research-related services.\n\n'
                'To learn more about ORCID, watch the [Why ORCID? video](https://vimeo.com/237730655) or visit their '
                '[website](https://orcid.org/content/help).\n\n'
                '## Connect your ORCID iD with your CoMSES Net account\n\n'
                'CoMSES Net would like to collect your ORCID iD for use in our systems. You can connect your CoMSES'
                ' Net account with ORCID and authorize the collection and use of your ORCID iD in our systems at your '
                '[account profile](/accounts/profile/) page or when you first sign up as a CoMSES Net member.\n\n\n'
                '## Why register your ORCID iD?\n\n'
                'Your ORCID iD:\n\n'
                '* distinguishes you and ensures your research outputs and activities are correctly attributed to you\n'
                '* reliably and easily connects you with your contributions and affiliations\n'
                '* reduces form-filling (enter data once, re-use it often)\n'
                '* improves recognition and discoverability for you and your research outputs\n'
                '* is interoperable (works with many institutions, funders, and publishers)\n'
                '* is persistent (enduring)\n'
                '* will allow us to integrate your publications, computational models, and research interests with your ORCID record\n\n'
                'An ORCID iD is also a requirement of many journal manuscript submission systems and grant application forms.\n\n\n'
                '--- Content adapted from [ORCID Communications Toolkit v4](https://doi.org/10.23640/07243.5493064.v4)\n\n\n'
            ),
        )
        parent.add_child(instance=orcid_page)

    def build(self):
        about_index = self.build_about_section()
        self.build_people_page(about_index)
        self.build_faq_page(about_index)
        self.build_contact_page(about_index)
        self.build_bylaws_page(about_index)
        self.build_orcid_page(about_index)


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

        landing_page = self.create_landing_page()
        # argparse converts dashes to underscores
        self.create_site(site_name=options['site_name'], hostname=options['site_domain'], root_page=landing_page)
        self.create_social_apps()
        # create community, about, resources pages
        for section in (CommunitySection, ResourceSection, AboutSection):
            section(self.landing_page, self.default_user).build()

    @staticmethod
    def create_social_apps():
        site = DjangoSite.objects.first()
        # set up orcid app social auth keys
        orcid_app, created = SocialApp.objects.get_or_create(
            provider='orcid',
            name='ORCID',
        )
        orcid_app.client_id = settings.ORCID_CLIENT_ID
        orcid_app.secret = settings.ORCID_CLIENT_SECRET
        orcid_app.sites.add(site)
        # set up github app social auth keys
        github_app, created = SocialApp.objects.get_or_create(
            provider='github',
            name='GitHub'
        )
        github_app.client_id = settings.GITHUB_CLIENT_ID
        github_app.secret = settings.GITHUB_CLIENT_SECRET
        github_app.sites.add(site)

    def create_site(self, site_name, hostname, root_page=None):
        if root_page is None:
            root_page = self.landing_page
        site = Site.objects.first() if Site.objects.count() > 0 else Site()
        site.site_name = site_name
        site.hostname = hostname
        site.is_default_site = True
        site.root_page = root_page
        site.save()
        sms = SocialMediaSettings.for_site(site)
        sms.youtube_url = 'https://www.youtube.com/user/CoMSESNet/'
        sms.twitter_account = 'openabm_comses'
        sms.mailing_list_url = 'http://eepurl.com/b8GCUv'
        sms.contact_form_recipients = ['editors@openabm.org']
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
            community_statement=COMMUNITY_STATEMENT,
        )
        for codebase in Codebase.objects.peer_reviewed():
            # if there are multiple images, just pull the first
            fc_dict = codebase.as_featured_content_dict()
            if fc_dict.get('codebase_image'):
                landing_page.featured_content_queue.add(FeaturedContentItem(**fc_dict))
        # refresh from DB before adding more nodes so treebeard can clean up its internals
        # https://django-treebeard.readthedocs.io/en/latest/caveats.html
        root_page.refresh_from_db()
        root_page.add_child(instance=landing_page)
        self.landing_page = landing_page
        return landing_page
