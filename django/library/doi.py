import csv
import logging
import re
import requests

from collections import defaultdict

from django.conf import settings
from huey.contrib.djhuey import on_commit_task

from .models import (
    Codebase,
    CodebaseRelease,
    DataCiteAction,
    DataCiteSchema,
    DataCiteRegistrationLog,
)

from datacite import DataCiteRESTClient, schema45
from datacite.errors import (
    DataCiteError,
    DataCiteNoContentError,
    DataCiteBadRequestError,
    DataCiteUnauthorizedError,
    DataCiteForbiddenError,
    DataCiteNotFoundError,
    DataCiteGoneError,
    DataCitePreconditionError,
    DataCiteServerError,
)

logger = logging.getLogger(__name__)

IS_DEVELOPMENT = settings.DEPLOY_ENVIRONMENT.is_development
IS_STAGING = settings.DEPLOY_ENVIRONMENT.is_staging
IS_PRODUCTION = settings.DEPLOY_ENVIRONMENT.is_production

# prefix differs across (dev + staging) and production
DATACITE_PREFIX = settings.DATACITE_PREFIX
DOI_PATTERN = re.compile(f"{DATACITE_PREFIX}/[-._;()/:a-zA-Z0-9]+")

MAX_DATACITE_API_WORKERS = 25

VERIFICATION_MESSAGE = r"""
                _  __       _                         
               (_)/ _|     (_)                        
__   _____ _ __ _| |_ _   _ _ _ __   __ _             
\ \ / / _ \ '__| |  _| | | | | '_ \ / _` |            
 \ V /  __/ |  | | | | |_| | | | | | (_| |  _   _   _ 
  \_/ \___|_|  |_|_|  \__, |_|_| |_|\__, | (_) (_) (_)
                       __/ |         __/ |            
                      |___/         |___/             
"""


def get_welcome_message(dry_run: bool):
    ENV_MESSAGE = ""
    if IS_DEVELOPMENT:
        ENV_MESSAGE = r"""
        +-+-+-+-+-+-+-+-+-+-+-+
        |D|E|V|E|L|O|P|M|E|N|T|
        +-+-+-+-+-+-+-+-+-+-+-+
        Development Mode
        """
    if IS_STAGING:
        ENV_MESSAGE = r"""
        (                             (        )          
        )\ )  *   )    (      (       )\ )  ( /(  (       
        (()/(` )  /(    )\     )\ )   (()/(  )\()) )\ )    
        /(_))( )(_))((((_)(  (()/(    /(_))((_)\ (()/(    
        (_)) (_(_())  )\ _ )\  /(_))_ (_))   _((_) /(_))_  
        / __||_   _|  (_)_\(_)(_)) __||_ _| | \| |(_)) __| 
        \__ \  | |     / _ \    | (_ | | |  | .` |  | (_ | 
        |___/  |_|    /_/ \_\    \___||___| |_|\_|   \___|

        Staging Mode
        """
    if IS_PRODUCTION:
        ENV_MESSAGE = r"""
        (   (       ) (                       (       )     ) 
        )\ ))\ ) ( /( )\ )          (    *   ))\ ) ( /(  ( /( 
        (()/(()/( )\()|()/(     (    )\ ` )  /(()/( )\()) )\())
        /(_))(_)|(_)\ /(_))    )\ (((_) ( )(_))(_)|(_)\ ((_)\ 
        (_))(_))   ((_|_))_  _ ((_))\___(_(_()|_))   ((_) _((_)
        | _ \ _ \ / _ \|   \| | | ((/ __|_   _|_ _| / _ \| \| |
        |  _/   /| (_) | |) | |_| || (__  | |  | | | (_) | .` |
        |_| |_|_\ \___/|___/ \___/  \___| |_| |___| \___/|_|\_|

        Production Mode
        """
    return f"""{ENV_MESSAGE}\n\n
            Dry Run Mode: {'On' if dry_run else 'Off'}\n
            """


def print_console_message(dry_run: bool, interactive: bool):
    print(get_welcome_message(dry_run))
    if interactive:
        input("Press Enter to continue or CTRL+C to quit...")


def is_valid_doi(doi: str) -> bool:
    # checks if DOI is formatted like this "00.12345/q2xt-rj46"
    if doi:
        return bool(re.match(DOI_PATTERN, doi, re.IGNORECASE))
    return False


@on_commit_task()
def schedule_mint_public_doi(release: CodebaseRelease, dry_run: bool = False):
    """
    Mint a DOI for the given release.

    Args:
        release (CodebaseRelease): The release for which to mint a DOI.
        dry_run (bool, optional): Flag indicating whether the operation should be performed in dry run mode.
            Defaults to False.

    Returns:
        A tuple of DataCiteRegistrationLog or None and a boolean indicating whether the operation was successful
    """
    if dry_run:
        return "XX.DRYXX/XXXX-XRUN"
    return DataCiteApi(dry_run=dry_run).mint_public_doi(release)


class DataCiteApi:
    """
    Wrapper around the datacite package:
    https://datacite.readthedocs.io/

    This class provides methods to interact with the DataCite REST API for minting DOIs, updating metadata,
    and checking metadata consistency.

    Attributes:
        datacite_client (DataCiteRESTClient): The DataCite REST API client.
        dry_run (bool): Flag indicating whether the operations should be performed in dry run mode.
    """

    # this is only needed right now because incoming DataCiteErrors do not keep track of the status code
    # maps datacite error classes to the http status codes that caused them
    DATACITE_ERRORS_TO_STATUS_CODE = defaultdict(
        lambda: 500,
        {
            DataCiteNoContentError: 204,
            DataCiteBadRequestError: 400,
            DataCiteUnauthorizedError: 401,
            DataCiteForbiddenError: 403,
            DataCiteNotFoundError: 404,
            DataCiteGoneError: 410,
            DataCitePreconditionError: 412,
            DataCiteServerError: 500,
        },
    )

    def __init__(self, dry_run=True):
        """
        Initializes a new instance of the DataCiteApi class.

        Args:
            dry_run (bool, optional): Flag indicating whether the operations should be performed in dry run mode.
                Defaults to True.

        Raises:
            Exception: If failed to access the DataCite API.
        """
        self.datacite_client = DataCiteRESTClient(
            username=settings.DATACITE_API_USERNAME,
            password=settings.DATACITE_API_PASSWORD,
            prefix=settings.DATACITE_PREFIX,
            test_mode=settings.DATACITE_TEST_MODE,
        )

        self.dry_run = dry_run

        if not self.is_datacite_available():
            raise Exception("Failed to access DataCite API!")

    def is_datacite_available(self) -> bool:
        """
        Checks if the DataCite API is available.

        Returns:
            bool: True if the DataCite API is working, False otherwise.
        """
        try:
            headers = {"accept": "text/plain"}
            response = requests.get(self._datacite_heartbeat_url, headers=headers)
            logger.debug("DataCite API heartbeat: %s", response.text)
            return response.text == "OK"
        except Exception:
            return False

    @property
    def _datacite_heartbeat_url(self):
        return (
            "https://api.datacite.org/heartbeat"
            if IS_PRODUCTION and not self.dry_run
            else "https://api.test.datacite.org/heartbeat"
        )

    def _validate_metadata(self, datacite_metadata: DataCiteSchema):
        metadata_dict = datacite_metadata.to_dict()
        try:
            schema45.validator.validate(metadata_dict)
        except Exception as e:
            logger.error(
                "Invalid DataCite metadata: %s", schema45.tostring(metadata_dict), e
            )
            raise DataCiteError(f"Invalid DataCite metadata: {metadata_dict}")
        return datacite_metadata, metadata_dict

    def mint_public_doi(self, codebase_or_release: Codebase | CodebaseRelease):
        """
        Mint a public DOI for the given codebase or release.

        Args:
            codebase_or_release (Codebase | CodebaseRelease): The codebase or release for which to mint a DOI.

        Returns:
            tuple: A tuple containing the DOI and a boolean indicating if the minting was successful.
        """
        if self.dry_run:
            return "XX.DRYXX/XXXX-XRUN", True
        if hasattr(codebase_or_release, "datacite"):
            del codebase_or_release.datacite

        doi = "Unassigned"
        http_status = 200
        message = "Minted new DOI successfully."

        datacite_metadata = codebase_or_release.datacite

        try:
            datacite_metadata, metadata_dict = self._validate_metadata(
                datacite_metadata
            )
            doi = self.datacite_client.public_doi(
                metadata_dict, url=codebase_or_release.permanent_url
            )
            codebase_or_release.doi = doi
            codebase_or_release.save()
        except DataCiteError as e:
            logger.error(e)
            message = str(e)
            http_status = self.DATACITE_ERRORS_TO_STATUS_CODE[type(e)]

        # refresh DataCiteMetadata to include new DOI in hash
        del codebase_or_release.datacite
        datacite_metadata = codebase_or_release.datacite
        log_record_dict = {
            "doi": doi,
            "http_status": http_status,
            "message": message,
            "metadata_hash": datacite_metadata.hash(),
        }
        if isinstance(codebase_or_release, Codebase):
            log_record_dict.update(
                codebase=codebase_or_release, action=DataCiteAction.CREATE_CODEBASE_DOI
            )
        elif isinstance(codebase_or_release, CodebaseRelease):
            log_record_dict.update(
                release=codebase_or_release, action=DataCiteAction.CREATE_RELEASE_DOI
            )
        return self._save_log_record(**log_record_dict), http_status == 200

    @classmethod
    def is_metadata_stale(cls, codebase_or_release: Codebase | CodebaseRelease):
        """
        Returns true if the metadata for the given codebase or release (based on the metadata hash) is out of date with
        its latest log entry
        """
        try:
            newest_log_entry = DataCiteRegistrationLog.objects.latest_entry(
                codebase_or_release
            )
            # always force refresh cached datacite property in case it was computed earlier
            if hasattr(codebase_or_release, "datacite"):
                del codebase_or_release.datacite
            return newest_log_entry.metadata_hash != codebase_or_release.datacite.hash()

        except DataCiteRegistrationLog.DoesNotExist:
            # no logs for this item, metadata is stale
            logger.info("No registration logs available for %s", codebase_or_release)

        return True

    def update_doi_metadata(self, codebase_or_release: Codebase | CodebaseRelease):
        """
        Returns a (DataCiteRegistrationLog, bool) tuple where the boolean indicates if the metadata was successfully updated.
        """
        if not self.is_metadata_stale(codebase_or_release):
            logger.info("No need to update DOI metadata for %s", codebase_or_release)
            return DataCiteRegistrationLog(), True
        doi = codebase_or_release.doi
        if self.dry_run:
            logger.debug("DRY RUN")
            logger.debug(
                "Updating DOI metadata for codebase_or_release: %s", codebase_or_release
            )
            logger.debug("Metadata: %s", codebase_or_release.datacite)
            return DataCiteRegistrationLog(), True
        if hasattr(codebase_or_release, "datacite"):
            del codebase_or_release.datacite
        datacite_metadata, metadata_dict = self._validate_metadata(
            codebase_or_release.datacite
        )
        http_status = 200
        message = f"Successfully updated metadata for {doi}."
        updated_metadata_dict = {"attributes": {**metadata_dict}}
        try:
            self.datacite_client.put_doi(doi, updated_metadata_dict)
            logger.debug("Successfully updated metadata for DOI: %s", doi)
        except DataCiteError as e:
            logger.error(e)
            message = f"Unable to update metadata for {doi}: {e}"
            http_status = self.DATACITE_ERRORS_TO_STATUS_CODE[type(e)]
        log_record_dict = {
            "doi": doi,
            "http_status": http_status,
            "message": message,
            "metadata_hash": datacite_metadata.hash(),
        }
        # FIXME: figure out how to better tie parameters to the requested action
        if isinstance(codebase_or_release, Codebase):
            log_record_dict.update(
                codebase=codebase_or_release,
                action=DataCiteAction.UPDATE_CODEBASE_METADATA,
            )
        elif isinstance(codebase_or_release, CodebaseRelease):
            log_record_dict.update(
                release=codebase_or_release,
                action=DataCiteAction.UPDATE_RELEASE_METADATA,
            )
        log = self._save_log_record(**log_record_dict)
        return log, http_status == 200

    @staticmethod
    def _is_deep_inclusive(elem1, elem2):
        if isinstance(elem1, dict):
            if not isinstance(elem2, dict):
                return False
            for key, value in elem1.items():
                # FIXME: affiliations for contributors will be returned as object only if '&affiliation=true' is present in the request.
                # Is there a way to set it when using datacite package?
                # https://support.datacite.org/docs/can-i-see-more-detailed-affiliation-information-in-the-rest-api
                if key == "affiliation":
                    return True
                if key not in elem2:
                    return False
                if not DataCiteApi._is_deep_inclusive(value, elem2[key]):
                    return False
        elif isinstance(elem1, list):
            if not isinstance(elem2, list):
                return False
            if elem1 and isinstance(elem1[0], dict):
                if not (elem2 and isinstance(elem2[0], dict)):
                    return False

                if len(elem1) != len(elem2):
                    return False

                sort_key = next(iter(elem1[0]))
                elem1_sorted = sorted(elem1, key=lambda x: x[sort_key])
                elem2_sorted = sorted(elem2, key=lambda x: x[sort_key])

                for el1, el2 in zip(elem1_sorted, elem2_sorted):
                    if not DataCiteApi._is_deep_inclusive(el1, el2):
                        return False
            else:
                return set(elem1).issubset(set(elem2))
        elif isinstance(elem2, int):
            # publicationYear is returned as int from DataCite
            return str(elem1) == str(elem2)
        elif elem1 != elem2:
            return False
        return True

    @staticmethod
    def is_metadata_equivalent(comses_metadata, datacite_metadata):
        """
        Checks if the metadata attributes in the sent_data dictionary are the same as the
        corresponding attributes in the received_data dictionary.

        Args:
            comses_metadata (dict): A DataCite-compatible dictionary drawn from CoMSES metadata for a given Codebase or CodebaseRelease.
            datacite_metadata (dict): A DataCite delivered dictionary pulled for a given DOI

        Returns:
            bool: True if all attributes are the same, False otherwise.
        """
        # Extract keys (attributes) from both dictionaries
        sent_keys = set(comses_metadata.keys())
        received_keys = set(datacite_metadata.keys())

        # Initialize array to store different attributes
        different_attributes = []

        # Check if all attributes in sent_data are present in received_data
        if sent_keys.issubset(received_keys):
            # Check if values of corresponding keys are the same
            for key in sent_keys:
                if key == "publicationYear":
                    # publicationYear is returned as int from DataCite
                    # FIXME: this accounts for publicationYear: None or "" sent to DataCite
                    EMPTY_VALS = [None, 0, "None", "0"]

                    if comses_metadata[key] and datacite_metadata[key]:
                        if str(comses_metadata[key]) != str(datacite_metadata[key]):
                            different_attributes.append(key)
                    elif not (
                        comses_metadata[key] in EMPTY_VALS
                        and datacite_metadata[key] in EMPTY_VALS
                    ):
                        different_attributes.append(key)
                    else:
                        continue

                if not DataCiteApi._is_deep_inclusive(
                    comses_metadata[key], datacite_metadata[key]
                ):
                    # if sent_data[key] != received_data[key]:

                    # FIXME: identifiers is not considered by the Fabrica API...
                    # FIXME: rightsList is enhanced by DataCite

                    if key != "identifiers" and key != "rightsList":
                        different_attributes.append(key)

            if different_attributes:
                logger.debug("Some attributes have different values:")
                for attr in different_attributes:
                    logger.debug(
                        f"Attribute '{attr}':\nSent value - {comses_metadata[attr]}\n"
                        f"Received value - {datacite_metadata[attr]}\n\n"
                    )
                return False
            else:
                return True
        else:
            logger.debug("Some attributes are missing.")
            missing_attributes = sent_keys.difference(received_keys)
            logger.debug("Missing attributes:", missing_attributes)
            return False

    def get_datacite_metadata(self, doi: str):
        """
        Get the metadata for the given DOI.

        Args:
            doi (str): The DOI for which to get the metadata.

        Returns:
            dict: The metadata for the given DOI.
        """
        return self.datacite_client.get_metadata(doi)

    def check_metadata(self, codebase_or_release: Codebase | CodebaseRelease) -> bool:
        """
        1. get metadata for item.doi
        2. compare if the values match codebase.datacite.metadata

        - item: Codebase | CodebaseRelease
        """
        if self.dry_run:
            logger.debug(
                "Dry run metadata check for %s", codebase_or_release.datacite.to_dict()
            )
            return True
        if not codebase_or_release.doi:
            logger.warning(
                "Unnecessary metadata check for non-DOI codebase or release %s",
                codebase_or_release,
            )
            return False
        try:
            comses_metadata = codebase_or_release.datacite.to_dict()
            datacite_metadata = self.get_datacite_metadata(codebase_or_release.doi)
            logger.debug(
                "comparing datacite metadata\n\n%s\n\nwith comses metadata\n\n%s",
                datacite_metadata,
                comses_metadata,
            )
            return DataCiteApi.is_metadata_equivalent(
                comses_metadata, datacite_metadata
            )
        except Exception as e:
            logger.error(e)
            return False

    def validate_metadata(self, items):
        for item in items:
            if item.doi:
                yield (item, self.check_metadata(item))

    def _save_log_record(
        self,
        action,
        doi,
        http_status,
        message,
        metadata_hash,
        release=None,
        codebase=None,
    ):
        item = release or codebase
        logger.debug(
            "DOI action: %s for item=%s, http_status=%s",
            action,
            item,
            http_status,
        )

        if not self.dry_run:
            return DataCiteRegistrationLog.objects.create(
                release=release,
                codebase=codebase,
                doi=doi,
                action=action,
                http_status=http_status,
                message=message,
                metadata_hash=metadata_hash,
            )
        return None

    def mint_pending_dois(self):
        """
        for ALL published peer_reviewed releases without DOIs:
        1. Mint DOI for parent codebase, if codebase.doi doesn’t exist.
        2. Mint DOI for release.
        3. Update metadata for parent codebase and sibling releases
        """

        peer_reviewed_releases_without_dois = (
            CodebaseRelease.objects.public().reviewed().without_doi()
        )

        total_peer_reviewed_releases_without_dois = (
            peer_reviewed_releases_without_dois.count()
        )
        logger.info(
            "Minting DOIs for %s peer reviewed releases without DOIs",
            total_peer_reviewed_releases_without_dois,
        )

        invalid_releases = []
        for i, release in enumerate(peer_reviewed_releases_without_dois):
            logger.debug(
                "Processing release %s/%s - %s",
                i + 1,
                total_peer_reviewed_releases_without_dois,
                release.pk,
            )
            if self.dry_run:
                logger.debug("DRY RUN - SKIPPING RELEASE %s", release.pk)
                continue

            codebase = release.codebase
            codebase_doi = codebase.doi

            """
            Mint DOI for parent codebase if it doesn't already exist
            """
            if not codebase_doi:
                mint_codebase_doi_log, ok = self.mint_public_doi(codebase)
                if not ok:
                    logger.error(
                        "Could not mint DOI for parent codebase %s. Skipping release %s.",
                        codebase.pk,
                        release.pk,
                    )
                    invalid_releases.append(
                        (
                            release,
                            mint_codebase_doi_log,
                            "Unable to mint DOI for parent codebase",
                        )
                    )

            """
            Mint DOI for release
            """
            mint_release_doi_log, ok = self.mint_public_doi(release)
            if not ok:
                logger.error("Could not mint DOI for release %s. Skipping.", release.pk)
                invalid_releases.append(
                    (release, mint_release_doi_log, "Unable to mint DOI for release")
                )
                continue

            logger.debug(
                "Updating metadata for parent codebase of release %s", release.pk
            )
            """
            Update parent Codebase metadata for new release DOI
            """
            codebase.refresh_from_db()
            release.refresh_from_db()
            update_codebase_doi_log, ok = self.update_doi_metadata(codebase)
            if not ok:
                logger.error("Failed to update metadata for codebase %s", codebase.pk)
                invalid_releases.append(
                    (
                        release,
                        update_codebase_doi_log,
                        "Failed to update codebase metadata",
                    )
                )

            """
            Update sibling metadata for new release DOI
            """
            logger.debug("Updating metadata for siblings of release %s", release.pk)

            previous_release = release.get_previous_release()
            next_release = release.get_next_release()

            if previous_release and previous_release.doi:
                update_previous_release_doi_log, ok = self.update_doi_metadata(
                    previous_release
                )
                if not ok:
                    logger.error(
                        "Failed to update metadata for previous_release %s",
                        previous_release.pk,
                    )
                    invalid_releases.append(
                        (
                            release,
                            update_previous_release_doi_log.http_status,
                            f"Unable to update previous release id {previous_release.pk} metadata {update_previous_release_doi_log.message}",
                        )
                    )

            if next_release and next_release.doi:
                update_next_release_doi_log, ok = self.update_doi_metadata(next_release)
                if not ok:
                    logger.error(
                        "Failed to update metadata for next_release %s", next_release.pk
                    )
                    invalid_releases.append(
                        (
                            release,
                            mint_codebase_doi_log.http_status,
                            f"Unable to update next release id {next_release.pk} metadata {update_next_release_doi_log.message}",
                        )
                    )

        logger.info(
            "Minted %s DOIs for peer reviewed releases without DOIs.",
            total_peer_reviewed_releases_without_dois,
        )
        if invalid_releases:
            with open("mint_pending_dois__invalid_pending_releases.csv", "w") as f:
                writer = csv.writer(f)
                writer.writerow(["release_id", "status_code", "message"])
                for release, status_code, message in invalid_releases:
                    writer.writerow([release.pk, status_code, message])

        """
        sanity check for all peer reviewed releases without DOIs and their parent codebases have valid DOIs
        """
        if not self.dry_run:
            print(VERIFICATION_MESSAGE)
            logger.info(
                "Verifying: all peer reviewed releases without DOIs and their parent codebases have valid DOIs"
            )
            invalid_codebases = []
            invalid_releases = []

            for i, release in enumerate(peer_reviewed_releases_without_dois):
                logger.debug(
                    "Verifying release: %s / %s",
                    i + 1,
                    total_peer_reviewed_releases_without_dois,
                )

                if not release.doi or not is_valid_doi(release.doi):
                    invalid_releases.append(release.pk)
                if not release.codebase.doi or not is_valid_doi(release.codebase.doi):
                    invalid_codebases.append(release.codebase.pk)

            if invalid_codebases:
                logger.error(
                    "FAILURE: %s Codebases with invalid or missing DOIs: %s",
                    len(invalid_codebases),
                    invalid_codebases,
                )
            else:
                logger.info(
                    "SUCCESS: All parent codebases of peer reviewed releases without DOIs have valid DOIs."
                )
            if invalid_releases:
                logger.error(
                    "FAILURE: %s CodebaseReleases with invalid or missing DOIs: %s",
                    len(invalid_releases),
                    invalid_releases,
                )
            else:
                logger.info(
                    "SUCCESS: All peer reviewed releases without DOIs have valid DOIs."
                )
