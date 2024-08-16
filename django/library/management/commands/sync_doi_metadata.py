import logging
from django.core.management.base import BaseCommand
from library.models import CodebaseRelease, Codebase, DataciteRegistrationLog
from library.doi import DataCiteApi, VERIFICATION_MESSAGE, get_welcome_message

logger = logging.getLogger(__name__)


def update_stale_metadata_for_all_codebases_with_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)
    all_codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.info(
        f"Updating stale metadata for all codebases with DOIs ({len(all_codebases_with_dois)}). Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            f"Processing Codebase {i+1}/{len(all_codebases_with_dois)}: codebase.pk={codebase.pk} ..."
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if DataciteRegistrationLog.is_metadata_stale(codebase):
            logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_codebase(codebase)
            if not ok:
                logger.error(f"Failed to update metadata for codebase {codebase.pk}")
            else:
                logger.debug(f"Metadata successfully updated.")
        else:
            logger.debug(f"Metadata is in sync. Skipping...")

    logger.info(
        f"Updated {len(all_codebases_with_dois)} codebases with stale metadata."
    )
    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            f"Checking that: metadata for all codebases with DOIs is in sync with DataCite..."
        )

        results = datacite_api.threaded_metadata_check(all_codebases_with_dois)

        if all([is_meta_valid for pk, is_meta_valid in results]):
            logger.info(
                f"Success. Metadata for all codebases with DOIs is in sync with DataCite."
            )


def update_stale_metadata_for_all_releases_with_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    datacite_api = DataCiteApi()
    all_releases_with_dois = CodebaseRelease.objects.exclude(doi__isnull=True)

    logger.debug(
        f"Updating stale metadata for all releases with DOIs ({len(all_releases_with_dois)}). Query: CodebaseRelease.objects.exclude(doi__isnull=True) ..."
    )

    for i, release in enumerate(all_releases_with_dois):
        logger.debug(
            f"Processing Release {i+1}/{len(all_releases_with_dois)}: release.pk={release.pk} ..."
        )

        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if DataciteRegistrationLog.is_metadata_stale(release):
            logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_release(release)
            if not ok:
                logger.error(f"Failed to update metadata for release {release.pk}")
            else:
                logger.debug(f"Metadata successfully updated.")
        else:
            logger.debug(f"Metadata is in sync. Skipping...")

        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")
        continue

    logger.info(f"Updated {len(all_releases_with_dois)} releases with stale metadata.")

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            f"Checking that: metadata for all releases with DOIs is in sync with DataCite..."
        )

        results = datacite_api.threaded_metadata_check(all_releases_with_dois)

        if all([is_meta_valid for pk, is_meta_valid in results]):
            logger.info(
                f"Success. Metadata for all releases with DOIs is in sync with DataCite."
            )


class Command(BaseCommand):
    """
    Syncs metadata for all codebases and releases with Datacite metadata service.
    """

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
        update_stale_metadata_for_all_codebases_with_dois(interactive, dry_run)
        update_stale_metadata_for_all_releases_with_dois(interactive, dry_run)
