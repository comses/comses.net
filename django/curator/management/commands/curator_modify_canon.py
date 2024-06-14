import logging

from django.core.management.base import BaseCommand

from curator.tag_deduplication import TagClusterManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Matches tags to a canonical list of tags using dedupe. This command finds a canonical tag "

    def handle(self, *args, **options):
        TagClusterManager.console_canonicalize_edit()
