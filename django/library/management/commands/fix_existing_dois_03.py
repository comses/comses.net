from django.core.management.base import BaseCommand
from django.conf import settings
import logging

from library.models import CodebaseRelease
from library.doi import (
    DataCiteApi,
    VERIFICATION_MESSAGE,
    doi_matches_pattern,
    get_welcome_message,
)


logger = logging.getLogger(__name__)


def update_existing_dois(interactive=True, dry_run=True):
    """
    Updates existing DOIs for peer reviewed CodebaseReleases and their parent Codebases.

    1. Mint a conceptual parent DOI for a given release's parent codebase and assign it to the Codebase
    2.
    """
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)

    peer_reviewed_releases = CodebaseRelease.objects.reviewed().with_doi()
    total_peer_reviewed_releases_count = peer_reviewed_releases.count()

    logger.info(
        "Updating DOIs for %s peer reviewed CodebaseReleases with DOIs",
        total_peer_reviewed_releases_count,
    )

    for i, release in enumerate(peer_reviewed_releases):
        logger.debug(
            "Processing release %s (%s / %s)...",
            release.pk,
            i + 1,
            total_peer_reviewed_releases_count,
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        # always refresh from DB in case a previous operation changed a parent Codebase's DOI
        release.refresh_from_db()
        codebase = release.codebase
        codebase.refresh_from_db()
        codebase_doi = codebase.doi

        """
        Mint DOI for codebase(parent) if it doesn't exist. 
        All Codebase DOIs should be reset before this operation
        """
        if not codebase_doi:
            # request to DataCite API
            logger.debug("Minting DOI for parent codebase: %s", codebase.pk)
            codebase_doi, success = datacite_api.mint_new_doi_for_codebase(codebase)

            if not success:
                logger.error(
                    "Could not mint DOI for parent codebase %s. Skipping release %s.",
                    codebase.pk,
                    release.pk,
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug("New codebase DOI: %s. Saving codebase...", codebase_doi)
            if not dry_run:
                codebase.doi = codebase_doi
                codebase.save()
        else:
            logger.debug(
                "Parent codebase %s already has a DOI %s - Skipping...",
                codebase.pk,
                codebase_doi,
            )

        """
        Verify release DOI itself. Update release DOIs with legacy handle.net DOIs
        """
        release_doi = release.doi

        if settings.DATACITE_PREFIX in release_doi:
            # update release metadata in DataCite
            # ok = datacite_api.update_metadata_for_release(release)
            # if not ok:
            #     logger.error("Could not update DOI metadata for release {release.pk}, DOI: {release_doi}. Error: {message}. Skipping.")
            #     continue
            logger.debug(
                "Release %s already has a valid DataCite DOI %s. Skipping...",
                release.pk,
                release.doi,
            )
            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")
            continue

        elif "2286.0" in release_doi:
            # FIXME: there is only one release with a DOI that matches this pattern, fix it in the db and remove this unnecessary check
            # handle legacy handle.net DOIs
            logger.debug(
                "Release %s has a handle.net DOI: (%s). Minting new DOI for release...",
                release.pk,
                release_doi,
            )
            # set up DataCite API request to mint new DOI
            release_doi, success = datacite_api.mint_new_doi_for_release(release)
            if not success:
                logger.error(
                    "Could not mint DOI for release %s. DOI: %s. Skipping.",
                    release.pk,
                    release_doi,
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug(
                "Saving new doi %s for release %s. Previous doi: %s",
                release_doi,
                release.pk,
                release.doi,
            )
            if not dry_run:
                release.doi = release_doi
                release.save()

            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")
            continue
        else:
            logger.debug(
                "Release %s has an invalid DOI: (%s). Minting new DOI for release...",
                release.pk,
                release_doi,
            )
            # request to DataCite API: mint new DOI!
            release_doi, success = datacite_api.mint_new_doi_for_release(release)
            if not success:
                logger.error(
                    "Could not mint DOI for release %s. DOI: %s. Skipping.",
                    release.pk,
                    release_doi,
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug(
                "Saving new doi %s for release %s. Previous doi: %s",
                release_doi,
                release.pk,
                release.doi,
            )
            if not dry_run:
                release.doi = release_doi
                release.save()
            continue

    logger.info(
        "Successfully fixed DOIs for existing %s peer reviewed CodebaseReleases with DOIs and their Codebases.",
        peer_reviewed_releases.count(),
    )

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking that all existing peer reviewed releases with DOIs (and their parent codebases) have valid DOIs"
        )
        for i, release in enumerate(peer_reviewed_releases):
            logger.debug(
                "Processing Codebase %s/%s - %s",
                i,
                peer_reviewed_releases.count(),
                "" if (i + 1) % 8 == 0 else "." * ((i + 1) % 8),
            )
            if release.codebase.doi is None:
                logger.error(
                    "Codebase DOI should not be None for codebase %s",
                    release.codebase.pk,
                )

            if release.doi is None:
                logger.error("DOI should not be None for release %s", release.pk)

            if not doi_matches_pattern(release.codebase.doi):
                logger.error(
                    "%s Codebase DOI doesn't match DataCite pattern!",
                    release.codebase.doi,
                )

            if not doi_matches_pattern(release.doi):
                logger.error(
                    "%s CodebaseRelease DOI doesn't match DataCite pattern!",
                    release.doi,
                )

        logger.info(
            "Success. All existing peer reviewed releases with DOIs (and their parent codebases) have valid DOIs now."
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
        update_existing_dois(interactive, dry_run)
