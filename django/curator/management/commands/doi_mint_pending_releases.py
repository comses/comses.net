from django.core.management.base import BaseCommand
from library.doi import DataCiteApi, VERIFICATION_MESSAGE, get_welcome_message

import argparse
import logging

logger = logging.getLogger(__name__)


def mint_pending_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    if interactive:
        input(
            "Minting new DOIs for all reviewed releases and parent codebases without DOIs. Press Enter to continue or CTRL+C to quit..."
        )
    api = DataCiteApi(dry_run)
    api.mint_pending_dois()
    print(VERIFICATION_MESSAGE)


class Command(BaseCommand):
    """
    Syncs metadata for all codebases and releases with Datacite metadata service.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action=argparse.BooleanOptionalAction,
            help="Wait for explicit user confirmation to continue.",
            default=True,
        )
        parser.add_argument(
            "--dry-run",
            action=argparse.BooleanOptionalAction,
            help="Emit what would have happened.",
            default=True,
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        logger.info("minting new DOIs for reviewed releases without DOIs")
        mint_pending_dois(interactive, dry_run)
