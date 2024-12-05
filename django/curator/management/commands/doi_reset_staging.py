import argparse
import csv
import logging
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from library.doi import VERIFICATION_MESSAGE, get_welcome_message, DataCiteApi
from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


def reset_all_dois(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))
    if settings.DEPLOY_ENVIRONMENT.is_production:
        logger.error("This command is not allowed in production.")
        sys.exit()
    logger.info("(ENV: %s) Removing all DOIs", settings.DEPLOY_ENVIRONMENT)
    releases_with_dois = CodebaseRelease.objects.with_doi()
    codebases_with_dois = Codebase.objects.with_doi()
    confirm = input(
        "WARNING: this will remove ALL existing DOIs and is unrecoverable. Type 'DELETE' to continue or Ctrl+C to quit: "
    )
    if confirm.lower() == "delete":
        with open("deleted_codebase_dois.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Codebase ID", "Codebase DOI"])
            for codebase in codebases_with_dois:
                writer.writerow([codebase.pk, codebase.doi])
        Codebase.objects.update(doi=None)
        with open("deleted_release_dois.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["CodebaseRelease ID", "CodebaseRelease DOI"])
            for release in releases_with_dois:
                writer.writerow([release.pk, release.doi])
        CodebaseRelease.objects.update(doi=None)
    else:
        logger.info("Aborting.")
        sys.exit()

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        assert Codebase.objects.with_doi().count() == 0
        assert CodebaseRelease.objects.with_doi().count() == 0
        logger.info("Success. All existing codebase DOIs deleted.")

    """ Mint DOIs for all new Peer Reviewed Releases"""
    peer_reviewed_releases = CodebaseRelease.objects.reviewed().public()
    datacite_api = DataCiteApi(dry_run=dry_run)
    invalid_releases = []
    for release in peer_reviewed_releases:
        try:
            log, ok = datacite_api.mint_public_doi(release)
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
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        reset_all_dois(interactive, dry_run)
