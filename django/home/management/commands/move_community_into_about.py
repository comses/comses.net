"""
migrate community page from top level CategoryIndexPage into a child of the About CIP
"""

from django.core.management.base import BaseCommand
import logging

from home.models import CategoryIndexPage, MarkdownPage, ConferenceIndexPage,

logger = logging.getLogger(__name__)

DESCRIPTION = """
CoMSES Net is dedicated to fostering open and reproducible scientific computation through 
cyberinfrastructure and community development. Our mission is to improve the way we 
develop, document, and share computational models of social and ecological systems - 
building FAIR research software that helps us navigate understand our increasingly 
complex world.
"""

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
        about_page.add_child(instance=community_page)
        community_page.heading = 'CoMSES Net Community'
        community_page.description = DESCRIPTION
        community_page.save()
        # need to set navigation_links in every subsidiary page of the about page,
        # annoyingly. There should be a better way to do this in wagtail perhaps
        # using wagtailmenus


