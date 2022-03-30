"""
management command to move education page from a community subpage to a top level
page under Home
"""

import logging

from django.core.management.base import BaseCommand

from wagtail.core.models import Page

from home.models import (
    MarkdownPage,
    CategoryIndexPage,
    PlatformIndexPage,
    JournalIndexPage,
)

logger = logging.getLogger(__name__)

RESOURCES_NAVIGATION_LINKS = (
    ("Resources", "/resources/"),
    ("Modeling Frameworks", "/resources/modeling-frameworks/"),
    ("Journals", "/resources/journals/"),
    ("Standards", "/resources/standards/"),
    ("Videos", "https://www.youtube.com/user/comsesnet/playlists"),
    ("Bibliometrics", "https://catalog.comses.net"),
)

EDUCATION_PAGE_DESCRIPTION = """
These CoMSES Net tutorials provide hands-on training in best practices for computational modeling and concrete guidance on tools and techniques to share your work and develop advanced data analysis workflows in accordance with the [FAIR principles for research software](https://doi.org/10.15497/RDA00068).

You must be logged in as a COMSES Net member to access these tutorials and have an up-to-date CoMSES Profile. 

Eligible users will receive a certificate of completion and digital badge after successfully completing a tutorial and its accompanying assessment.
"""

EDUCATION_PAGE_BODY = """
## 1. [FAIR practices for computational modeling](https://github.com/comses/winter-school-2022/blob/main/initial-tutorial/README.md)
[This tutorial](https://github.com/comses/winter-school-2022/blob/main/initial-tutorial/README.md) provides an introduction to the FAIR principles for research software and concrete practices to help you make your computational models more FAIR.

### Assessment
Read [this document](https://docs.google.com/document/d/1EVTLEWdsxnPUXwYzeBDOoGB-2x9QP-EG-SkUWPv1ECE/edit?usp=sharing) and answer the [associated questions](https://forms.gle/5WjshdE2QXXpRhRh9).

## 2. Introduction to GitHub

[Join this GitHub classroom](https://classroom.github.com/a/SF1_14wJ) and complete the assignments to familiarize yourself with Git and GitHub. To join the classroom, click the link and associate your GitHub account with your classroom student roster entry.

If you are new to Git please download [GitHub Desktop](https://desktop.github.com/) to follow along with the GitHub Classroom assignments. We will use a NetLogo model as an example. You will also need a plain text editor like [Atom](https://atom.io/) or [Visual Studio Code](https://code.visualstudio.com/) to resolve git merge conflicts in NetLogo code as NetLogo will not be able to open those files.

## 3. Introduction to Containerization

[This tutorial](https://classroom.github.com/a/AIdYi37i) introduces the concept of _containerization_ and provides step-by-step guidance on how to containerize an example NetLogo model with transparency and longevity in mind.

## 4. GitHub Community Model

This GitHub repository is for an urban vulnerability project that has been used in several CoMSES Winter Schools. Learn to use GitHub tools in a collaborative computational model of governance and vulnerability in an urban setting.

https://github.com/comses/urban-vulnerability 
"""


class Command(BaseCommand):

    """
    Move existing Education page from under Resources to a top level Page
    """

    def handle(self, *args, **options):
        education_page = MarkdownPage.objects.get(slug="education")
        home_page = Page.objects.get(slug="home")
        education_page.title = "Educational Resources"
        education_page.heading = "Educational Resources"
        education_page.description = EDUCATION_PAGE_DESCRIPTION
        education_page.body.raw = EDUCATION_PAGE_BODY
        education_page.move(home_page, pos="last-child")
        education_page.breadcrumbs.all().delete()
        education_page.navigation_links.all().delete()
        education_page.add_breadcrumbs((("Educational Resources", ""),))
        # remove education from resources subnavigation links
        resources_page = CategoryIndexPage.objects.get(slug="resources")
        resources_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # frameworks
        frameworks_page = PlatformIndexPage.objects.first()
        frameworks_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # journals
        journals_page = JournalIndexPage.objects.first()
        journals_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # standards
        standards_page = MarkdownPage.objects.get(slug="standards")
        standards_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)

        for page in (
            education_page,
            resources_page,
            frameworks_page,
            journals_page,
            standards_page,
        ):
            page.save()
