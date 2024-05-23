"""
migrate community page from top level CategoryIndexPage into a child of the About CIP
"""

from django.core.management.base import BaseCommand
import logging

from home.models import (
    CategoryIndexPage,
    ConferenceIndexPage,
    FaqPage,
    PeoplePage,
    ContactPage,
)

logger = logging.getLogger(__name__)

DESCRIPTION = """
CoMSES Net is dedicated to fostering open and reproducible scientific computation through 
cyberinfrastructure and community development. Our mission is to improve the way we 
develop, document, and share computational models of social and ecological systems - 
building FAIR research software that helps us navigate understand our increasingly 
complex world.
"""

ABOUT_NAVIGATION_LINKS = (
    ("About", "/about/"),
    ("People", "/about/people/"),
    ("Community", "/about/community/"),
    ("FAQ", "/about/faq/"),
    ("Contact", "/about/contact/"),
)


class Command(BaseCommand):
    """
    Adjust the Community page for  https://github.com/comses/comses.net/issues/584
    this can't be in a data migration for arcane wagtail reasons related to CategoryIndexPage subclassing
    wagtailcore.models.Page
    """

    def handle(self, *args, **options):
        community_page = CategoryIndexPage.objects.get(slug="community")
        conference_page = ConferenceIndexPage.objects.first()
        # remove all subnav links for conference page
        conference_page.navigation_links.all().delete()
        # update conference breadcrumb trail to about -> community -> conference
        conference_page.breadcrumbs.all().delete()
        conference_page.add_breadcrumbs(
            (
                ("About", "/about/"),
                ("Community", "/about/community/"),
                ("CoMSES Virtual Conferences", ""),
            )
        )
        community_page.breadcrumbs.all().delete()
        community_page.add_breadcrumbs((("About", "/about/"), ("Community", "")))

        about_page = CategoryIndexPage.objects.get(slug="about")
        community_page.heading = "CoMSES Net Community"
        community_page.summary = DESCRIPTION
        community_page.replace_navigation_links(ABOUT_NAVIGATION_LINKS)
        # need to set navigation_links in every subsidiary page of the about page,
        # annoyingly. There should be a better way to do this in wagtail perhaps
        # using wagtailmenus
        about_page.replace_navigation_links(ABOUT_NAVIGATION_LINKS)
        # adjust navlinks for /about/people/
        people_page = PeoplePage.objects.first()
        people_page.replace_navigation_links(ABOUT_NAVIGATION_LINKS)
        # FAQs
        faq_page = FaqPage.objects.first()
        faq_page.replace_navigation_links(ABOUT_NAVIGATION_LINKS)
        # contact
        contact_page = ContactPage.objects.first()
        contact_page.replace_navigation_links(ABOUT_NAVIGATION_LINKS)
        # move community page under about page
        community_page.move(about_page, pos="last-child")
        for page in (
            community_page,
            conference_page,
            about_page,
            people_page,
            faq_page,
            contact_page,
        ):
            page.save()
