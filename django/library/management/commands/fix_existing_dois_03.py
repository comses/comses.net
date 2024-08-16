import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

from library.models import CodebaseRelease
from library.doi import (
    DataCiteApi,
    VERIFICATION_MESSAGE,
    doi_matches_pattern,
    get_welcome_message,
)

logger = logging.getLogger(__name__)


def fix_existing_dois_03(interactive=True, dry_run=True):
    print(get_welcome_message(dry_run))

    datacite_api = DataCiteApi(dry_run=dry_run)

    peer_reviewed_releases_with_dois = CodebaseRelease.objects.filter(
        peer_reviewed=True
    ).filter(Q(doi__isnull=False) | Q(doi=""))

    logger.info(
        f'Fixing existing DOIs for {len(peer_reviewed_releases_with_dois)} peer reviewed CodebaseReleases with DOIs. Query: CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=False) | Q(doi="")) ...'
    )

    for i, release in enumerate(peer_reviewed_releases_with_dois):
        logger.debug(
            f"Processing release {i+1}/{len(peer_reviewed_releases_with_dois)}, release.pk={release.pk}..."
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        codebase = release.codebase
        codebase_doi = codebase.doi

        """
        Mint DOI for codebase(parent) if it doesn't exist. 
        Since we deleted all Codebase DOIs in 01_delete_all_existing_codebase_dois(), codebase_doi is None
        """
        if not codebase_doi:
            # request to DataCite API
            logger.debug(f"Minting DOI for parent codebase: {codebase.pk}...")
            codebase_doi = datacite_api.mint_new_doi_for_codebase(codebase)

            if not codebase_doi:
                logger.error(
                    f"Could not mint DOI for parent codebase {codebase.pk}. Skipping release {release.pk}."
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug(f"New codebase DOI: {codebase_doi}. Saving codebase...")

            if not dry_run:
                codebase.doi = codebase_doi
                codebase.save()
        else:
            logger.debug(
                f"Parent codebase: codebase.pk={codebase.pk} already has a DOI: {codebase.doi}. Skipping..."
            )

        """
        Handle DOI for release
        """
        release_doi = release.doi

        if settings.DATACITE_PREFIX in release_doi:
            # update release metadata in DataCite
            # ok = datacite_api.update_metadata_for_release(release)
            # if not ok:
            #     logger.error("Could not update DOI metadata for release {release.pk}, DOI: {release_doi}. Error: {message}. Skipping.")
            #     continue
            logger.debug(
                f"Release {release.pk} already has a valid DataCite DOI {release.doi}. Skipping..."
            )
            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")
            continue

        elif release_doi == "" or "2286.0" in release_doi:
            logger.debug(
                f"Release {release.pk} has an empty DOI or a hanlde.net DOI: ({release.doi}). Minting new DOI for release..."
            )
            # request to DataCite API: mint new DOI!
            release_doi = datacite_api.mint_new_doi_for_release(release)
            if not release_doi:
                logger.error(
                    "Could not mint DOI for release {release.pk}. Error: {message}. Skipping."
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug(
                f"Saving new doi {release_doi} for release {release.pk}. Previous doi: {release.doi}"
            )
            if not dry_run:
                release.doi = release_doi
                release.save()

            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")
            continue
        else:
            logger.debug(
                f"Release {release.pk} has a 'bad' DOI: ({release.doi}). Minting new DOI for release..."
            )
            # request to DataCite API: mint new DOI!
            release_doi = datacite_api.mint_new_doi_for_release(release)
            if not release_doi:
                logger.error(
                    "Could not mint DOI for release {release.pk}. Error: {message}. Skipping."
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            logger.debug(
                f"Saving new doi {release_doi} for release {release.pk}. Previous doi: {release.doi}"
            )
            if not dry_run:
                release.doi = release_doi
                release.save()
            continue

    logger.info(
        f"Successfully fixed DOIs for existing {len(peer_reviewed_releases_with_dois)} peer reviewed CodebaseReleases with DOIs and their Codebases."
    )

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            "Checking that  all existing peer reviewed releases with DOIs (and their parent codebases) have valid DOIs..."
        )
        for i, release in enumerate(peer_reviewed_releases_with_dois):
            print(
                f"Processing Codebase {i}/{len(peer_reviewed_releases_with_dois)} {'' if (i+1)%8 == 0 else '.'*((i+1)%8)}",
                end=" \r",
            )
            if release.codebase.doi is None:
                logger.error(
                    f"Codebase DOI should not be None for codebase {release.codebase.pk}"
                )

            if release.doi is None:
                logger.error(f"DOI should not be None for release {release.pk}")

            if not doi_matches_pattern(release.codebase.doi):
                logger.error(
                    f"{release.codebase.doi} Codebase DOI doesn't match DataCite pattern!"
                )

            if not doi_matches_pattern(release.doi):
                logger.error(
                    f"{release.doi} CodebaseRelease DOI doesn't match DataCite pattern!"
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
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Output what would have happened."
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        dry_run = options["dry_run"]
        fix_existing_dois_03(interactive, dry_run)
