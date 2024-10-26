import argparse
import csv
import logging
from django.core.management.base import BaseCommand

from library.models import Codebase
from library.doi import DataCiteApi, get_welcome_message

logger = logging.getLogger(__name__)


def sync_all_doi_metadata(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)
    all_codebases_with_dois = Codebase.objects.with_doi()
    total_number_of_codebases_with_dois = all_codebases_with_dois.count()
    invalid_codebases = []
    invalid_releases = []

    logger.info(
        "Updating metadata for all codebases (%s) with DOIs and their releases with DOIs. ...",
        total_number_of_codebases_with_dois,
    )

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            "Processing codebase %s - %s/%s",
            codebase.pk,
            i + 1,
            total_number_of_codebases_with_dois,
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        # first ensure parent codebase metadata is properly synced
        log, ok = datacite_api.update_doi_metadata(codebase)
        if not ok:
            logger.error("Failed to update metadata for codebase {codebase.pk}")
            invalid_codebases.append((codebase, log))

        # next check all parent codebase release metadata
        for j, release in enumerate(codebase.releases.with_doi()):
            logger.debug(
                "Processing release #%s (%s/%s)",
                release.pk,
                j + 1,
                codebase.releases.count(),
            )
            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")

            if release.peer_reviewed and release.doi:
                log, ok = datacite_api.update_doi_metadata(release)
                if not ok:
                    logger.error("Failed to update metadata for release %s", release.pk)
                    invalid_releases.append((release, log))
            else:
                logger.debug("Skipping unreviewed / no DOI release %s", release.pk)

    if invalid_codebases:
        with open("doi_sync_metadata_invalid_codebases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Codebase ID", "HTTP Status Code", "Message"])
            for codebase, log in invalid_codebases:
                writer.writerow([codebase.pk, log.status_code, log.message])
    if invalid_releases:
        with open("doi_sync_metadata_invalid_releases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["CodebaseRelease ID", "HTTP Status Code", "Message"])
            for release, log in invalid_releases:
                writer.writerow([release.pk, log.status_code, log.message])
    logger.info("Metadata updated for all existing Codebase + CodebaseRelease DOIs.")
    """
    FIXME: verify_metadata currently does not work with metadata responses from DataCite
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info("Checking that local metadata is in sync with DataCite...")
        with open("doi_update_metadata_invalid_codebases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Codebase ID", "DataCite metadata"])
            for codebase, valid_metadata in datacite_api.validate_metadata(
                all_codebases_with_dois
            ):
                if not valid_metadata:
                    logger.warning("inconsistent metadata for codebase %s", codebase.pk)
                    writer.writerow([codebase.pk, codebase.datacite.to_json()])

        all_releases_with_dois = CodebaseRelease.objects.with_doi()
        with open("doi_update_metadata_invalid_releases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["CodebaseRelease ID", "DataCite metadata"])
            for release, valid_metadata in datacite_api.validate_metadata(
                all_releases_with_dois
            ):
                if not valid_metadata:
                    logger.warning("inconsistent metadata for release %s", release.pk)
                    writer.writerow([release.pk, release.datacite.to_json()])
    """


class Command(BaseCommand):
    """
    Synchronizes DOI metadata for all Codebase and CodebaseRelease objects with existing DOIs.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action=argparse.BooleanOptionalAction,
            help="Wait for user to press enter to continue.",
            default=False,
        )
        parser.add_argument(
            "--dry-run",
            action=argparse.BooleanOptionalAction,
            help="Output what would have happened.",
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        sync_all_doi_metadata(interactive, dry_run)
