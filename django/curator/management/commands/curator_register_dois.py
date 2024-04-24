from django.core.management.base import BaseCommand

from library.doi import mint_dois_for_peer_reviewed_releases_without_dois

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mint DOIs for all peer reviewed codebase releases without a DOI"

    def handle(self, *args, **options):
        logger.debug("Registering all peer reviewed codebases")
        codebases = mint_dois_for_peer_reviewed_releases_without_dois()
        logger.debug("DOIs minted for %s", codebases)
