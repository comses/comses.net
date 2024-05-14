"""
add a link to the digest archive page in the about page(s)
this is a temporary home for the digests link until we figure out better navigation
"""

from django.core.management.base import BaseCommand
import logging

from home.models import (
    CategoryIndexPage,
    FaqPage,
    PeoplePage,
    ContactPage,
)

logger = logging.getLogger(__name__)

DIGEST_ARCHIVE_PAGE_LINK = [("Digest", "/digest/")]


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            about_pages = [
                CategoryIndexPage.objects.get(slug="community"),
                CategoryIndexPage.objects.get(slug="about"),
                PeoplePage.objects.first(),
                FaqPage.objects.first(),
                ContactPage.objects.first(),
            ]
            for page in about_pages:
                page.add_navigation_links(DIGEST_ARCHIVE_PAGE_LINK)
        except Exception as e:
            logger.error(f"Error adding digest link to about pages: {e}")
            raise
        for page in about_pages:
            page.save()
        logger.info("Successfully added digest link to about pages")
