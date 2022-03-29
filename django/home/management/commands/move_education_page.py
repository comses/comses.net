"""
Move education from

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


class Command(BaseCommand):

    """
    Move existing Education page from under Resources to a top level Page
    """

    def handle(self, *args, **options):
        education_page = MarkdownPage.objects.get(slug="education")
        home_page = Page.objects.get(slug="home")
        education_page.heading = "Educational Resources"
        education_page.move(home_page, pos="last-child")
        education_page.breadcrumbs.all().delete()
        education_page.navigation_links.all().delete()
        education_page.add_breadcrumbs((("Educational Resources", "/education/"),))
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
