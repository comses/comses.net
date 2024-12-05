import argparse
import csv
import logging
import sys
from django.core.management.base import BaseCommand
from library.doi import VERIFICATION_MESSAGE, get_welcome_message, DataCiteApi
from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


def cleanup_existing_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    api = DataCiteApi(dry_run=dry_run)

    # clean up all Codebases with existing DOIs
    codebases_with_dois = Codebase.objects.with_doi()
    logger.info("Removing all Codebase DOIs")
    if interactive and codebases_with_dois.exists():
        confirm = input(
            "WARNING: this will remove all existing codebase DOIs and is unrecoverable. Type 'DELETE' to continue or Ctrl+C to quit: "
        )
        if not confirm.lower() == "delete":
            logger.info("Aborting.")
            sys.exit()

    """
    assert that all Codebase DOIs have been reset
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        with open("cleanup_codebases_with_doi.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Codebase ID", "Codebase DOI"])
            for codebase in codebases_with_dois:
                writer.writerow([codebase.pk, codebase.doi])
        codebases_with_dois.update(doi=None)
        assert not Codebase.objects.with_doi().exists()
        logger.info("Success. All existing codebase DOIs deleted.")

    # clean up unreviewed release DOIs

    unreviewed_releases_with_dois = CodebaseRelease.objects.unreviewed().with_doi()
    total_unreviewed_releases_with_dois = unreviewed_releases_with_dois.count()
    logger.info(
        "Removing %s unreviewed CodebaseRelease DOIs",
        total_unreviewed_releases_with_dois,
    )
    if interactive:
        confirm = input(
            f"Deleting all DOIs for {total_unreviewed_releases_with_dois} unreviewed CodebaseReleases. Enter 'DELETE' to continue or CTRL+C to quit: "
        )
        if not confirm.lower() == "delete":
            logger.debug("Aborting...")
            sys.exit()

    if not dry_run:
        with open("cleanup_unreviewed_releases_with_doi.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["CodebaseRelease ID", "CodebaseRelease DOI"])
            for release in unreviewed_releases_with_dois:
                writer.writerow([release.pk, release.doi])
        unreviewed_releases_with_dois.update(doi=None)

    # mint DOIs for all public peer reviewed CodebaseReleases without a DOI
    reviewed_releases_without_dois = (
        CodebaseRelease.objects.reviewed().public().without_doi()
    )
    invalid_releases = []
    for release in reviewed_releases_without_dois:
        try:
            # make sure parent codebase has a DOI first
            release.refresh_from_db()
            codebase = release.codebase
            if not codebase.doi:
                log, ok = api.mint_public_doi(codebase)
                if not ok:
                    invalid_releases.append((codebase, log))
            log, ok = api.mint_public_doi(release)
            if not ok:
                invalid_releases.append((release, log))
        except Exception as e:
            logger.error("Error minting DOI for release %s", release)
            invalid_releases.append((release, e))

    for release, log in invalid_releases:
        with open("invalid_releases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["CodebaseRelease ID", "Status Code", "Reason", "Datacite Metadata"]
            )
            writer.writerow(
                [release.pk, log.http_status, log.message, release.datacite.to_dict()]
            )


class Command(BaseCommand):
    """
    Removes all existing parent Codebase DOIs and mints new DOIs for all Peer Reviewed CodebaseReleases
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action=argparse.BooleanOptionalAction,
            help="Wait for user to press enter to continue.",
            default=True,
        )
        parser.add_argument(
            "--dry-run",
            action=argparse.BooleanOptionalAction,
            help="Output what would have happened.",
            default=False,
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        cleanup_existing_dois(interactive, dry_run)
