import logging
from django.core.management.base import BaseCommand
from library.models import CodebaseRelease
from library.doi import (
    DataCiteApi,
    VERIFICATION_MESSAGE,
    doi_matches_pattern,
    get_welcome_message,
)

logger = logging.getLogger(__name__)


def mint_dois_for_peer_reviewed_releases_without_dois(interactive=True, dry_run=True):
    """
    for ALL peer_reviewed releases without DOIs:
    1. Mints DOI for parent codebase, if codebase.doi doesn’t exist.
    2. Mints DOI for release.
    3. Updates metadata for parent codebase and sibling releases
    """

    print(get_welcome_message(dry_run))
    datacite_api = DataCiteApi()

    # CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=True) | Q(doi=""))
    peer_reviewed_releases_without_dois = CodebaseRelease.objects.reviewed_without_doi()

    logger.info(
        f"Minting DOIs for peer reviewed releases without DOIs  ({len(peer_reviewed_releases_without_dois)}). Query: CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=True) | Q(doi="
        ")) ..."
    )

    for i, release in enumerate(peer_reviewed_releases_without_dois):
        logger.debug(
            f"Processing release {i+1}/{len(peer_reviewed_releases_without_dois)} release.pk={release.pk} ..."
        )
        if interactive:
            input("Press Enter to continue or CTRL+C to quit...")

        codebase = release.codebase
        codebase_doi = codebase.doi

        """
        Mint DOI for codebase(parent) if it doesn't exist.
        """
        if not codebase_doi:
            # request to DataCite API
            codebase_doi = datacite_api.mint_new_doi_for_codebase(codebase)

            if not codebase_doi:
                logger.error(
                    f"Could not mint DOI for parent codebase {codebase.pk}. Skipping release {release.pk}."
                )
                if interactive:
                    input("Press Enter to continue or CTRL+C to quit...")
                continue

            if not dry_run:
                codebase.doi = codebase_doi
                codebase.save()

        """
        Mint DOI for release
        """
        # request to DataCite API
        release_doi = datacite_api.mint_new_doi_for_release(release)
        if not release_doi:
            logger.error(f"Could not mint DOI for release {release.pk}. Skipping.")
            if interactive:
                input("Press Enter to continue or CTRL+C to quit...")
            continue

        if not dry_run:
            release.doi = release_doi
            release.save()

        logger.debug(f"Updating metadata for parent codebase of release {release.pk}")
        """
        Since a new DOI has been minted for the release, we need to update it's parent's metadata (HasVersion)
        """
        ok = datacite_api.update_metadata_for_codebase(codebase)
        if not ok:
            logger.error(f"Failed to update metadata for codebase {codebase.pk}")

        """
        Since a new DOI has been minted for the release, we need to update it's siblings' metadata (isNewVersionOf, isPreviousVersionOf)
        """
        logger.debug(f"Updating metadata for sibling releases of release {release.pk}")

        previous_release = release.get_previous_release()
        next_release = release.get_next_release()

        if previous_release and previous_release.doi:
            ok = datacite_api.update_metadata_for_release(previous_release)
            if not ok:
                logger.error(
                    f"Failed to update metadata for previous_release {previous_release.pk}"
                )

        if next_release and next_release.doi:
            ok = datacite_api.update_metadata_for_release(next_release)
            if not ok:
                logger.error(
                    f"Failed to update metadata for next_release {next_release.pk}"
                )

    logger.info(
        f"Minted {len(peer_reviewed_releases_without_dois)} DOIs for peer reviewed releases without DOIs."
    )

    """
    assert correctness
    """
    if not dry_run:
        print(VERIFICATION_MESSAGE)
        logger.info(
            f"Checking that: all peer reviewed releases (previously) without DOIs (and their parent codebases) have valid DOIs now..."
        )
        invalid_codebases = []
        invalid_releases = []

        for i, release in enumerate(peer_reviewed_releases_without_dois):
            print(
                f"Verifying release: {i}/{len(peer_reviewed_releases_without_dois)} {'' if (i+1)%8 == 0 else '.'*((i+1)%8)}",
                end=" \r",
            )

            if not release.doi or not doi_matches_pattern(release.doi):
                invalid_releases.append(release.pk)
            if not release.codebase.doi or not doi_matches_pattern(
                release.codebase.doi
            ):
                invalid_codebases.append(release.codebase.pk)

        if invalid_codebases:
            logger.error(
                f"Failure. Codebases with invalid or missing DOIs ({len(invalid_codebases)}): {invalid_codebases}"
            )
        else:
            logger.info(
                "Success. All parent codebases for peer reviewed releases previously without DOIs have valid DOIs now."
            )
        if invalid_releases:
            logger.error(
                f"Failure. CodebaseReleases with invalid or missing DOIs ({len(invalid_releases)}): {invalid_releases}"
            )
        else:
            logger.info(
                "Success. All peer reviewed releases previously without DOIs have valid DOIs now."
            )


class Command(BaseCommand):
    """
    Mints DOIs for all peer reviewed CodebaseReleases.
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
        mint_dois_for_peer_reviewed_releases_without_dois(interactive, dry_run)
