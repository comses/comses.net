import logging
from django.core.management.base import BaseCommand

from library.models import CodebaseRelease, Codebase, DataciteRegistrationLog
from library.doi import DataCiteApi, VERIFICATION_MESSAGE, get_welcome_message

logger = logging.getLogger(__name__)


def update_doi_metadata(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)
    all_codebases_with_dois = Codebase.objects.with_doi()

    logger.info(
        "Updating metadata for all codebases (%s) with DOIs and their releases with DOIs. ...",
        all_codebases_with_dois.count(),
    )

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            "Processing codebase %s - %s/%s",
            codebase.pk,
            i + 1,
            all_codebases_with_dois.count(),
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        if DataciteRegistrationLog.is_metadata_stale(codebase):
            logger.debug("Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_codebase(codebase)
            if not ok:
                logger.error("Failed to update metadata for codebase {codebase.pk}")
        else:
            logger.debug("Metadata for codebase {codebase.pk} is in sync!")

        for j, release in enumerate(codebase.releases.all()):
            logger.debug(
                "Processing release #%s (%s/%s)",
                release.pk,
                j + 1,
                codebase.releases.count(),
            )
            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")

            if release.peer_reviewed and release.doi:
                if DataciteRegistrationLog.is_metadata_stale(release):
                    logger.debug("Metadata is stale. Updating metadata in DataCite...")
                    ok = datacite_api.update_metadata_for_release(release)
                    if not ok:
                        logger.error(
                            "Failed to update metadata for release %s", release.pk
                        )
                else:
                    logger.debug("Metadata for release %s is synced", release.pk)
            else:
                if not release.doi:
                    logger.warning("Release has no DOI")
                if not release.peer_reviewed:
                    logger.warning("Release is not peer reviewed")

    logger.info("Metadata updated for all existing (Codebase & CodebaseRelease) DOIs.")
    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info("Checking that Comses metadata is in sync with DataCite...")
        invalid_codebases = []
        invalid_releases = []

        results = datacite_api.threaded_metadata_check(all_codebases_with_dois)
        for pk, is_meta_valid in results:
            if not is_meta_valid:
                invalid_codebases.append(pk)

        if invalid_codebases:
            logger.error(
                "Failure. Metadata not in sync with DataCite for %s codebases: %s",
                invalid_codebases.count(),
                invalid_codebases,
            )
        else:
            logger.info(
                "Success. Metadata in sync with DataCite for all codebases with DOI."
            )

        all_releases_with_dois = CodebaseRelease.objects.with_doi()
        results = datacite_api.threaded_metadata_check(all_releases_with_dois)
        for pk, is_meta_valid in results:
            if not is_meta_valid:
                invalid_releases.append(pk)

        if invalid_releases:
            logger.error(
                f"Failure. Metadata not in sync with DataCite for {len(invalid_releases)} releases: {invalid_releases}"
            )
        else:
            logger.info(
                f"Success. Metadata in sync with DataCite for all releases with DOI."
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
        update_doi_metadata(interactive, dry_run)
