"""
migrate community page from top level CategoryIndexPage into a child of the About CIP
"""

from django.core.management.base import BaseCommand
import logging

from home.models import (CategoryIndexPage, ConferenceIndexPage, FaqPage, PeoplePage, ContactPage)

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
        community_page.navigation_links.all().delete()
        conference_page = ConferenceIndexPage.objects.first()
        # remove all subnav links for conference page
        conference_page.navigation_links.all().delete()
        # update conference breadcrumb trail to about -> community -> conference
        conference_page.breadcrumbs.all().delete()
        conference_page.add_breadcrumbs(
            (('About', '/about/'), ('Community', '/about/community/'))
        )
        community_page.breadcrumbs.all().delete()

        about_page = CategoryIndexPage.objects.get(slug='about')
        community_page.move(about_page, pos='last-child')
        community_page.heading = 'CoMSES Net Community'
        community_page.description = DESCRIPTION
        community_page.add_navigation_links(ABOUT_NAVIGATION_LINKS)
        community_page.save()
        # need to set navigation_links in every subsidiary page of the about page,
        # annoyingly. There should be a better way to do this in wagtail perhaps
        # using wagtailmenus
        about_page.navigation_links.all().delete()
        about_page.add_navigation_links(
            ABOUT_NAVIGATION_LINKS
        )
        about_page.save()
        # adjust navlinks for /about/people/
        people_page = PeoplePage.objects.first()
        people_page.navigation_links.all().delete()
        people_page.add_navigation_links(
            ABOUT_NAVIGATION_LINKS
        )
        people_page.save()
        # FAQs
        faq_page = FaqPage.objects.first()
        faq_page.navigation_links.all().delete()
        faq_page.add_navigation_links(ABOUT_NAVIGATION_LINKS)
        faq_page.save()
        # contact
        contact_page = ContactPage.objects.first()
        contact_page.navigation_links.all().delete()
        contact_page.add_navigation_links(ABOUT_NAVIGATION_LINKS)
        contact_page.save()

