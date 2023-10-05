import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagClusterer, TagClusterManager


class Command(BaseCommand):
    # TODO: Expand upon this
    help = """
    Edit clusters.
    """

    def handle(self, *args, **options):
        """ """
        TagClusterManager.console_label()
