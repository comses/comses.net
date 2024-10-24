import logging
from django.core.management.base import BaseCommand
from library.doi import VERIFICATION_MESSAGE, get_welcome_message
from library.models import CodebaseRelease

logger = logging.getLogger(__name__)


def remove_dois_from_unreviewed_releases(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    unreviewed_releases_with_dois = CodebaseRelease.objects.filter(
        peer_reviewed=False, doi__isnull=False
    )
    total_unreviewed_releases_with_dois = unreviewed_releases_with_dois.count()

    logger.info(
        "Cleaning up DOIs for %s unreviewed CodebaseReleases with DOIs",
        total_unreviewed_releases_with_dois,
    )
    if interactive:
        confirm = input(
            "Deleting all DOIs for unreviewed CodebaseReleases. Enter 'DELETE' to continue or CTRL+C to quit: "
        )
        if confirm.lower() == "delete":
            unreviewed_releases_with_dois.update(doi=None)

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking that DOIs for all not peer reviewed releases have been deleted..."
        )
        assert (
            CodebaseRelease.objects.filter(
                peer_reviewed=False, doi__isnull=False
            ).count()
            == 0
        )
        logger.info(
            "All DOIs from not peer_reviewed CodebaseReleases %s with DOIs deleted successfully.",
            total_unreviewed_releases_with_dois,
        )


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Wait for user to press enter to continue.",
            default=True,
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Output what would have happened."
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        remove_dois_from_unreviewed_releases(interactive, dry_run)
