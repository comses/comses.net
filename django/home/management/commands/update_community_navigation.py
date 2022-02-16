"""
updates community page subnavigation linkages
"""

import logging

from django.core.management.base import BaseCommand

from home.models import CategoryIndexPage, ConferenceIndexPage

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    """
    Adjust the Community subnavigation links for https://github.com/comses/comses.net/issues/415
    this can't be in a data migration for arcane wagtail reasons related to CategoryIndexPage subclassing
    wagtailcore.models.Page
    """

    def handle(self, *args, **options):
        COMMUNITY_NAVIGATION_LINKS = (
            ("Community", "/community/"),
            ("Virtual Conferences", "/conference/"),
            ("CoMSES Digest", "/digest/"),
        )
        community_page = CategoryIndexPage.objects.get(slug="community")
        community_page.navigation_links.all().delete()
        # existing navigation link structure
        # 0 = Community
        # 1 = Forum
        # 2 = Users
        # 3 = Jobs
        # 4 = Newsletter
        # New structure:
        # 0 = Community
        # 1 = Virtual Conferences
        # 2 = CoMSES Digest
        # 3 = Forum
        community_page.add_navigation_links(COMMUNITY_NAVIGATION_LINKS)
        community_page.save()

        conference_index_page = ConferenceIndexPage.objects.first()
        conference_index_page.add_navigation_links(COMMUNITY_NAVIGATION_LINKS)
        conference_index_page.save()
