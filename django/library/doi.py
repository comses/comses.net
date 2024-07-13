import logging
import re
import time
import threading
import queue
import requests

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

from .models import (
    Codebase,
    CodebaseRelease,
    DataCiteAction,
    DataCiteMetadata,
    DataCiteRegistrationLog,
)

from datacite import DataCiteRESTClient, schema43
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

# prefix is different for (dev & staging) and production environments
DATACITE_PREFIX = settings.DATACITE_PREFIX

MAX_DATACITE_API_WORKERS = 25

VERIFICATION_MESSAGE = """
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
        ENV_MESSAGE = """
        +-+-+-+-+-+-+-+-+-+-+-+
        |D|E|V|E|L|O|P|M|E|N|T|
        +-+-+-+-+-+-+-+-+-+-+-+
        Development Mode is On
        """
    if IS_STAGING:
        ENV_MESSAGE = """
        (                             (        )          
        )\ )  *   )    (      (       )\ )  ( /(  (       
        (()/(` )  /(    )\     )\ )   (()/(  )\()) )\ )    
        /(_))( )(_))((((_)(  (()/(    /(_))((_)\ (()/(    
        (_)) (_(_())  )\ _ )\  /(_))_ (_))   _((_) /(_))_  
        / __||_   _|  (_)_\(_)(_)) __||_ _| | \| |(_)) __| 
        \__ \  | |     / _ \    | (_ | | |  | .` |  | (_ | 
        |___/  |_|    /_/ \_\    \___||___| |_|\_|   \___|

        Staging Mode is On
        """
    if IS_PRODUCTION:
        ENV_MESSAGE = """
        (   (       ) (                       (       )     ) 
        )\ ))\ ) ( /( )\ )          (    *   ))\ ) ( /(  ( /( 
        (()/(()/( )\()|()/(     (    )\ ` )  /(()/( )\()) )\())
        /(_))(_)|(_)\ /(_))    )\ (((_) ( )(_))(_)|(_)\ ((_)\ 
        (_))(_))   ((_|_))_  _ ((_))\___(_(_()|_))   ((_) _((_)
        | _ \ _ \ / _ \|   \| | | ((/ __|_   _|_ _| / _ \| \| |
        |  _/   /| (_) | |) | |_| || (__  | |  | | | (_) | .` |
        |_| |_|_\ \___/|___/ \___/  \___| |_| |___| \___/|_|\_|

        Production Mode is On
        """
    if dry_run:
        DRY_RUN_MESSAGE = """
        Dry Run Mode is On\n
        """
    else:
        DRY_RUN_MESSAGE = """
        Dry Run Mode is Off
        """
    return ENV_MESSAGE + DRY_RUN_MESSAGE


def doi_matches_pattern(doi: str) -> bool:
    # checks if DOI is formatted like this "00.12345/q2xt-rj46"
    pattern = re.compile(f"{DATACITE_PREFIX}/[-._;()/:a-zA-Z0-9]+")
    if re.match(pattern, doi):
        return True
    else:
        return False


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

    DATACITE_ERRORS_TO_STATUS_CODE = defaultdict(lambda: 500)
    DATACITE_ERRORS_TO_STATUS_CODE.update(
        {
            DataCiteNoContentError: 204,
            DataCiteBadRequestError: 400,
            DataCiteUnauthorizedError: 401,
            DataCiteForbiddenError: 403,
            DataCiteNotFoundError: 404,
            DataCiteGoneError: 410,
            DataCitePreconditionError: 412,
            DataCiteServerError: 500,
        }
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

    def _validate_metadata(self, datacite_metadata: DataCiteMetadata):
        metadata_dict = datacite_metadata.to_dict()
        if not schema43.validate(metadata_dict):
            logger.error("Invalid DataCite metadata: %s", metadata_dict)
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
        datacite_metadata, metadata_dict = self._validate_metadata(
            codebase_or_release.datacite
        )
        doi = "Unassigned"
        http_status = 200
        message = "Minted new DOI successfully."

        try:
            doi = self.datacite_client.public_doi(
                metadata_dict, url=codebase_or_release.permanent_url
            )
        except DataCiteError as e:
            logger.error(e)
            message = str(e)
            http_status = self.DATACITE_ERRORS_TO_STATUS_CODE[type(e)]

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
        self._save_log_record(**log_record_dict)
        return doi, http_status == 200

    def update_doi_metadata(self, codebase_or_release: Codebase | CodebaseRelease):
        doi = codebase_or_release.doi
        if self.dry_run:
            logger.debug("DRY RUN")
            logger.debug(
                "Updating DOI metadata for codebase_or_release: %s", codebase_or_release
            )
            logger.debug("Metadata: %s", codebase_or_release.datacite)
            return doi, True
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
            logger.debug("Successfully updated metadta for DOI: %s", doi)
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
        self._save_log_record(**log_record_dict)
        return http_status == 200

    def mint_new_doi_for_codebase(self, codebase: Codebase) -> str:
        return self.mint_public_doi(codebase)

    def mint_new_doi_for_release(self, release: CodebaseRelease) -> str:
        return self.mint_public_doi(release)

    def update_metadata_for_codebase(self, codebase: Codebase) -> bool:
        return self.update_doi_metadata(codebase)

    def update_metadata_for_release(self, release: CodebaseRelease) -> bool:
        return self.update_doi_metadata(release)

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
    def _is_same_metadata(sent_data, received_data):
        """
        Checks if the metadata attributes in the sent_data dictionary are the same as the
        corresponding attributes in the received_data dictionary.

        Args:
            sent_data (dict): The dictionary containing the sent metadata attributes.
            received_data (dict): The dictionary containing the received metadata attributes.

        Returns:
            bool: True if all attributes are the same, False otherwise.
        """
        # Extract keys (attributes) from both dictionaries
        sent_keys = set(sent_data.keys())
        received_keys = set(received_data.keys())

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

                    if sent_data[key] and received_data[key]:
                        if str(sent_data[key]) != str(received_data[key]):
                            different_attributes.append(key)
                    elif not (
                        sent_data[key] in EMPTY_VALS
                        and received_data[key] in EMPTY_VALS
                    ):
                        different_attributes.append(key)
                    else:
                        continue

                if not DataCiteApi._is_deep_inclusive(
                    sent_data[key], received_data[key]
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
                        f"Attribute '{attr}':\nSent value - {sent_data[attr]}\n"
                        f"Received value - {received_data[attr]}\n\n"
                    )
                return False
            else:
                return True
        else:
            logger.debug("Some attributes are missing.")
            missing_attributes = sent_keys.difference(received_keys)
            logger.debug("Missing attributes:", missing_attributes)
            return False

    def check_metadata(self, item) -> bool:
        """
        1. get metadata for item.doi
        2. compare if the values match codebase.datacite.metadata

        - item: Codebase | CodebaseRelease
        """
        if not item.doi:
            return False
        try:
            if not self.dry_run:
                comses_metadata = item.datacite.to_dict()
                datacite_metadata = self.datacite_client.get_metadata(item.doi)
                return DataCiteApi._is_same_metadata(comses_metadata, datacite_metadata)
            else:
                logger.debug(
                    f"{'Codebase' if isinstance(item, Codebase) else 'CodebaseRelease'} metadata is in sync!"
                )
                return True
        except Exception as e:
            logger.error(e)
            return False

    def threaded_metadata_check(self, items):
        def loading_animation(thread):
            while thread.is_alive():
                print(".", end="", flush=True)
                time.sleep(0.1)
            print("\n")

        def _check_metadata(q: queue.Queue):
            with ThreadPoolExecutor(max_workers=MAX_DATACITE_API_WORKERS) as executor:
                results = executor.map(
                    lambda item: (item.pk, self.check_metadata(item)), items
                )

            q.put(results)

        # Create a queue to pass data between threads
        result_queue = queue.Queue()

        # Start the long-running function in a separate thread
        thread = threading.Thread(target=_check_metadata, args=(result_queue,))
        thread.start()

        # Display the loading animation in the main thread
        loading_animation(thread)

        # Wait for the long-running function to finish
        thread.join()
        # Get the results from the queue
        results = result_queue.get()
        return results

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
            "logging DOI action %s for item=%s, http_status=%s",
            action,
            item,
            http_status,
        )

        if not self.dry_run:
            DataCiteRegistrationLog.objects.create(
                release=release,
                codebase=codebase,
                doi=doi,
                action=action,
                http_status=http_status,
                message=message,
                metadata_hash=metadata_hash,
            )
