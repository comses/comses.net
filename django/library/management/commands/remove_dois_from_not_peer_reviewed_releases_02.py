import logging
from django.core.management.base import BaseCommand
from library.models import CodebaseRelease
from library.doi import VERIFICATION_MESSAGE, get_welcome_message

logger = logging.getLogger(__name__)


def remove_dois_from_not_peer_reviewed_releases_02(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    not_peer_reviewed_releases_with_dois = CodebaseRelease.objects.filter(
        peer_reviewed=False
    ).filter(doi__isnull=False)

    logger.info(
        f"Cleaning up DOIs for {len(not_peer_reviewed_releases_with_dois)} not peer_reviewed CodebaseReleases with DOIs. Query: CodebaseRelease.objects.filter(peer_reviewed=False).filter(doi__isnull=False) ..."
    )

    for i, release in enumerate(not_peer_reviewed_releases_with_dois):
        logger.debug(
            f"Deleting DOI {i+1}/{len(not_peer_reviewed_releases_with_dois)}: {release.doi} from release {release.pk} ..."
        )

        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")
        if not dry_run:
            release.doi = None
            release.save()

    logger.info(
        f"All DOIs from not peer_reviewed CodebaseReleases ({len(not_peer_reviewed_releases_with_dois)}) with DOIs deleted successfully."
    )
    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking that DOIs for all not peer reviewed releases have been deleted..."
        )
        for i, release in enumerate(not_peer_reviewed_releases_with_dois):
            print(
                f"Processing Codebase {i}/{len(not_peer_reviewed_releases_with_dois)} {'' if (i+1)%8 == 0 else '.'*((i+1)%8)}",
                end=" \r",
            )
            if release.doi is not None:
                logger.error(
                    f"DOI for not peer reviewed release {release.pk} should be None!"
                )
        logger.info(
            "Success. All existing DOIs for non peer reviewed releases have been deleted."
        )


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Wait for user to press enter to continue.",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Output what would have happened."
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        remove_dois_from_not_peer_reviewed_releases_02(interactive, dry_run)
