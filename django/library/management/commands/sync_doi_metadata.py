from django.core.management.base import BaseCommand
from library.doi import DataCiteApi, VERIFICATION_MESSAGE, get_welcome_message
from library.models import CodebaseRelease, Codebase, DataciteRegistrationLog

import logging

logger = logging.getLogger(__name__)


def update_stale_metadata_for_all_codebases_with_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)
    all_codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)
    total_codebases_count = all_codebases_with_dois.count()

    logger.info(
        "Updating stale metadata for %s codebases with DOIs",
        total_codebases_count,
    )

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            "Processing Codebase with pk %s (%s/%s)...",
            codebase.pk,
            i + 1,
            total_codebases_count,
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if DataciteRegistrationLog.is_metadata_stale(codebase):
            logger.debug("Metadata is stale. Updating metadata in DataCite...")
            success = datacite_api.update_metadata_for_codebase(codebase)
            if not success:
                logger.error("Failed to update metadata for codebase %s", codebase.pk)
            else:
                logger.debug("Metadata successfully updated.")
        else:
            logger.debug("Metadata is in sync. Skipping...")

    logger.info("Updated all codebases with stale metadata.")
    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking that metadata for all codebases with DOIs is in sync with DataCite..."
        )

        results = datacite_api.threaded_metadata_check(all_codebases_with_dois)

        if all([is_meta_valid for pk, is_meta_valid in results]):
            logger.info(
                "Success. Metadata for all codebases with DOIs is in sync with DataCite."
            )


def update_stale_metadata_for_all_releases_with_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    datacite_api = DataCiteApi()
    all_releases_with_dois = CodebaseRelease.objects.exclude(doi__isnull=True)
    total_releases_count = all_releases_with_dois.count()

    logger.debug(
        "Updating stale metadata for %s releases with DOIs",
        total_releases_count,
    )

    for i, release in enumerate(all_releases_with_dois):
        logger.debug(
            "Processing Release id %s (%s / %s)",
            release.pk,
            i + 1,
            total_releases_count,
        )

        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if DataciteRegistrationLog.is_metadata_stale(release):
            logger.debug("Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_release(release)
            if not ok:
                logger.error("Failed to update metadata for release %s", release.pk)
            else:
                logger.debug("Metadata successfully updated.")
        else:
            logger.debug("Metadata is up-to-date. Skipping...")

        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")
        continue

    logger.info("Updated all releases with stale metadata.")

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking metadata for all releases with DOIs is in sync with DataCite..."
        )

        results = datacite_api.threaded_metadata_check(all_releases_with_dois)

        if all([is_meta_valid for pk, is_meta_valid in results]):
            logger.info(
                "Success. Metadata for all releases with DOIs is in sync with DataCite."
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
            default=True,
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Output what would have happened."
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        update_stale_metadata_for_all_codebases_with_dois(interactive, dry_run)
        update_stale_metadata_for_all_releases_with_dois(interactive, dry_run)
