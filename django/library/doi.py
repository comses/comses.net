import logging
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
import requests

from django.conf import settings

from .models import (
    Codebase,
    CodebaseRelease,
    DataciteAction,
    DataciteRegistrationLog,
)

from datacite import DataCiteRESTClient, schema43
from datacite.errors import *

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

def get_welcome_message(dry_run:bool):
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
    """

    def __init__(self, dry_run=True):
        """
        Get a DataCite REST API client
        """
        self.datacite_client = DataCiteRESTClient(
            username=settings.DATACITE_API_USERNAME,
            password=settings.DATACITE_API_PASSWORD,
            prefix=settings.DATACITE_PREFIX,
            test_mode=settings.DATACITE_TEST_MODE,
        )

        self.dry_run = dry_run

        if not self.heartbeat():
            logger.error("Failed to access DataCite API!")
            raise Exception("Failed to access DataCite API!")

    def heartbeat(self) -> bool:
        # Check if DataCite API is working
        try:
            datacite_heartbeat_url = "https://api.test.datacite.org/heartbeat"
            if not self.dry_run and IS_PRODUCTION:
                datacite_heartbeat_url = "https://api.datacite.org/heartbeat"

            headers = {"accept": "text/plain"}
            response = requests.get(datacite_heartbeat_url, headers=headers)
            logger.debug(f"DataCite API heartbeat: {response.text}")

            if response.text == "OK":
                return True
            else:
                return False

        except Exception as e:
            return False

    def mint_new_doi_for_codebase(self, codebase: Codebase) -> str:
        action = DataciteAction.CREATE_CODEBASE_DOI
        doi, _ = self._call_datacite_api(action, codebase)
        return doi

    def mint_new_doi_for_release(self, release: CodebaseRelease) -> str:
        action = DataciteAction.CREATE_RELEASE_DOI
        doi, _ = self._call_datacite_api(action, release)
        return doi

    def update_metadata_for_codebase(self, codebase: Codebase) -> bool:
        action = DataciteAction.UPDATE_CODEBASE_METADATA
        _, ok = self._call_datacite_api(action, codebase)
        return ok

    def update_metadata_for_release(self, release: CodebaseRelease) -> bool:
        action = DataciteAction.UPDATE_RELEASE_METADATA
        _, ok = self._call_datacite_api(action, release)
        return ok

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

        except DataCiteError as de:
            logger.error(str(de))
            return False
        except Exception as e:
            logger.error(str(e))
            return False

    def threaded_metadata_check(self, items):
        def loading_animation(thread):
            while thread.is_alive():
                print(".", end="", flush=True)
                time.sleep(0.1)
            print("\n")

        def _check_metadata(q: queue.Queue):
            with ThreadPoolExecutor(max_workers=MAX_DATACITE_API_WORKERS) as executor:
                results = executor.map(lambda item: (item.pk, self.check_metadata(item)), items)

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

    def _call_datacite_api(self, action: DataciteAction, item):
        """
        item can be Codebase or CodebaseRelease
        """
        doi = None
        http_status = None
        message = None
        metadata_hash = None

        logger.debug(f"_call_datacite_api({action}, {type(item)}, pk={item.pk})")
        try:
            # remove from cache
            if hasattr(item, "datacite"):
                del item.datacite

            metadata_dict = item.datacite.to_dict()
            metadata_hash = item.datacite.to_hash()

            # validate metadta. Will throw AssertionError (will not call DataCite) if metadata is invalid.
            assert schema43.validate(metadata_dict), "Metadata is invalid!"

            if (
                action == DataciteAction.CREATE_RELEASE_DOI
                or action == DataciteAction.CREATE_CODEBASE_DOI
            ):
                if self.dry_run:
                    doi = "XX.XXXXX/XXXX-XXXX"
                else:
                    if IS_STAGING or IS_DEVELOPMENT:
                        doi = self.datacite_client.draft_doi(metadata_dict)

                    if IS_PRODUCTION:
                        doi = self.datacite_client.public_doi(
                            metadata_dict, url=item.permanent_url
                        )

                logger.debug(f"New DOI minted: {doi}")
                http_status = 200
            elif (
                action == DataciteAction.UPDATE_RELEASE_METADATA
                or action == DataciteAction.UPDATE_CODEBASE_METADATA
            ):
                doi = item.doi

                if not self.dry_run:
                    metadata_dict_enhanced = {"attributes": {**metadata_dict}}
                    self.datacite_client.put_doi(item.doi, metadata_dict_enhanced)

                logger.debug(f"Metadata successfully updated for DOI: {item.doi}")
                http_status = 200
            else:
                raise Exception("DataCite action unknown!")

        except DataCiteNoContentError as dc_nce:
            logger.info(dc_nce)
            http_status = 204
            message = str(dc_nce)

        except DataCiteBadRequestError as cd_bre:
            logger.error(cd_bre)
            http_status = 400
            message = str(cd_bre)

        except DataCiteUnauthorizedError as dc_ue:
            logger.error(dc_ue)
            http_status = 401
            message = str(dc_ue)

        except DataCiteForbiddenError as dc_fe:
            logger.error(dc_fe)
            http_status = 403
            message = str(dc_fe)

        except DataCiteNotFoundError as dc_nfe:
            logger.error(dc_nfe)
            http_status = 404
            message = str(dc_nfe)

        except DataCiteGoneError as dc_ge:
            logger.error(dc_ge)
            http_status = 410
            message = str(dc_ge)

        except DataCitePreconditionError as dc_pe:
            logger.error(dc_pe)
            http_status = 412
            message = str(dc_pe)

        except DataCiteServerError as dc_se:
            logger.error(dc_se)
            http_status = 500
            message = str(dc_se)

        except Exception as e:
            # unexpected exception
            logger.error(e)
            http_status = 600
            message = str(e)

        self._save_log_record(
            action=action,
            doi=doi,
            http_status=http_status,
            message=message,
            metadata_hash=metadata_hash,
            release=item if isinstance(item, CodebaseRelease) else None,
            codebase=item if isinstance(item, Codebase) else None,
        )

        ok = True
        if http_status > 200:
            ok = False

        return doi, ok

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
            f"save_log_record(action={action}, item={type(item)}, http_status={http_status})"
        )

        if not self.dry_run:
            # Create DataciteRegistrationLog record
            DataciteRegistrationLog.objects.create(
                release=release,
                codebase=codebase,
                doi=doi,
                action=action,
                http_status=http_status,
                message=message,
                metadata_hash=metadata_hash,
            )