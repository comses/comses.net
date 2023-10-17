import logging

from django.core.management.base import BaseCommand
from taggit.models import Tag

from curator.tag_deduplication import TagGazetteer, TagClusterManager
from curator.models import CanonicalTag, CanonicalTagMapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Matches tags to a canonical list of tags using dedupe. This command finds a canonical tag "

    def handle(self, *args, **options):
        TagClusterManager.console_canonicalize_edit()
