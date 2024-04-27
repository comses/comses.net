import logging
import re
import requests

from django.conf import settings
from django.db.models import Q

from .models import (
    Codebase,
    CodebaseRelease,
    DataciteAction,
    DataciteRegistrationLog,
)

from datacite import DataCiteRESTClient, schema43
from datacite.errors import *

logger = logging.getLogger(__name__)

DRY_RUN = True if settings.DATACITE_DRY_RUN == "true" else False
IS_STAGING = settings.DEPLOY_ENVIRONMENT.is_staging
IS_PRODUCTION = settings.DEPLOY_ENVIRONMENT.is_production

DATACITE_PREFIX = settings.DATACITE_PREFIX


if DRY_RUN:
    WELCOME_MESSAGE = """
    DDDDD   RRRRR   YYY   YYY     RRRRR    UU   UU   NN   NN 
    DD   DD RR   RR  YY   YY      RR   RR  UU   UU   NNN  NN 
    DD   DD RRRRR     YYYYY       RRRRR    UU   UU   NN N NN 
    DD   DD RR   RR    YYY        RR   RR  UU   UU   NN  NNN 
    DDDDD   RR    RR   YYY        RR    RR  UUUUU    NN   NN 

    Dry Run Mode is On
    """
elif IS_STAGING:
    WELCOME_MESSAGE = """
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
elif IS_PRODUCTION:
    WELCOME_MESSAGE = """
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

    def __init__(self):
        """
        Get a DataCite REST API client
        """
        self.datacite_client = DataCiteRESTClient(
            username=settings.DATACITE_API_USERNAME,
            password=settings.DATACITE_API_PASSWORD,
            prefix=settings.DATACITE_PREFIX,
            test_mode=settings.DATACITE_TEST_MODE,
        )

        if not self.heartbeat():
            logger.error("Failed to access DataCite API!")
            raise Exception("Failed to access DataCite API!")

    def heartbeat(self) -> bool:
        # Check if DataCite API is working
        try:
            datacite_heartbeat_url = "https://api.test.datacite.org/heartbeat"
            if not DRY_RUN and IS_PRODUCTION:
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
                logger.debug("All sent and received attributes match.")
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
            if not DRY_RUN:
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
                if DRY_RUN:
                    doi = "XX.XXXXX/XXXX-XXXX"

                if IS_STAGING and not DRY_RUN:
                    doi = self.datacite_client.draft_doi(metadata_dict)

                if IS_PRODUCTION and not DRY_RUN:
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

                if not DRY_RUN:
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

        if not DRY_RUN:
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


"""
ONE-TIME TASKS
"""


def delete_all_existing_codebase_dois_01():
    print(WELCOME_MESSAGE)
    codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.debug(
        f"Deleting DOIs for {len(codebases_with_dois)} Codebases. Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )
    input("Press Enter to continue...")

    for i, codebase in enumerate(codebases_with_dois):
        logger.debug(
            f"Deleting DOI {i+1}/{len(codebases_with_dois)}: {codebase.doi} from codebase {codebase.pk} ..."
        )

        if not DRY_RUN:
            codebase.doi = None
            codebase.save()

        logger.debug(f"DOI deleted.")
        input("Press Enter to continue...")

    if not DRY_RUN:
        """
        assert correctness
        """
        for codebase in codebases_with_dois:
            assert (
                codebase.doi is None
            ), f"DOI for codebase {codebase.pk} should be None!"


def remove_dois_from_not_peer_reviewed_releases_02():
    print(WELCOME_MESSAGE)

    not_peer_reviewed_releases_with_dois = CodebaseRelease.objects.filter(
        peer_reviewed=False
    ).filter(doi__isnull=False)

    logger.debug(
        f"Cleaning up DOIs for {len(not_peer_reviewed_releases_with_dois)} not peer_reviewed CodebaseReleases with DOIs. Query: CodebaseRelease.objects.filter(peer_reviewed=False).filter(doi__isnull=False) ..."
    )
    input("Press Enter to continue...")

    for i, release in enumerate(not_peer_reviewed_releases_with_dois):
        logger.debug(
            f"Deleting DOI {i+1}/{len(not_peer_reviewed_releases_with_dois)}: {release.doi} from release {release.pk} ..."
        )

        if not DRY_RUN:
            release.doi = None
            release.save()

        logger.debug(f"DOI deleted.")
        input("Press Enter to continue...")

    if not DRY_RUN:
        """
        assert correctness
        """
        for release in not_peer_reviewed_releases_with_dois:
            assert (
                release.doi is None
            ), f"DOI for not peer reviewed release {release.pk} should be None!"


def fix_existing_dois_03():
    print(WELCOME_MESSAGE)

    datacite_api = DataCiteApi()

    peer_reviewed_releases_with_dois = CodebaseRelease.objects.filter(
        peer_reviewed=True
    ).filter(Q(doi__isnull=False) | Q(doi=""))

    logger.debug(
        f'Fixing existing DOIs for {len(peer_reviewed_releases_with_dois)} peer reviewed CodebaseReleases with DOIs. Query: CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=False) | Q(doi="")) ...'
    )
    input("Press Enter to continue...")

    for i, release in enumerate(peer_reviewed_releases_with_dois):
        logger.debug(
            f"Processing release {i+1}/{len(peer_reviewed_releases_with_dois)}, release.pk={release.pk}..."
        )
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
                input("Press Enter to continue...")
                continue

            logger.debug(f"New codebase DOI: {codebase_doi}. Saving codebase...")

            if not DRY_RUN:
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

        if DATACITE_PREFIX in release_doi:
            # update release metadata in DataCite
            # ok = datacite_api.update_metadata_for_release(release)
            # if not ok:
            #     logger.error("Could not update DOI metadata for release {release.pk}, DOI: {release_doi}. Error: {message}. Skipping.")
            #     continue
            logger.debug(
                f"Release {release.pk} already has a valid DataCite DOI {release.doi}. Skipping..."
            )
            input("Press Enter to continue...")
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
                input("Press Enter to continue...")
                continue

            logger.debug(
                f"Saving new doi {release_doi} for release {release.pk}. Previous doi: {release.doi}"
            )
            if not DRY_RUN:
                release.doi = release_doi
                release.save()

            input("Press Enter to continue...")
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
                input("Press Enter to continue...")
                continue

            logger.debug(
                f"Saving new doi {release_doi} for release {release.pk}. Previous doi: {release.doi}"
            )
            if not DRY_RUN:
                release.doi = release_doi
                release.save()

            input("Press Enter to continue...")
            continue
            # logger.warning(
            #     f"Unknown DOI! Release {release.pk} with doi {release_doi} will not be handled by this script."
            # )
            # input("Press Enter to continue...")
            # continue

    """
    assert correctness
    """
    print(VERIFICATION_MESSAGE)

    if not DRY_RUN:
        for release in peer_reviewed_releases_with_dois:
            assert (
                release.codebase.doi is not None
            ), f"Codebase DOI should not be None for codebase {release.codebase.pk}"

            assert (
                release.doi is not None
            ), f"DOI should not be None for release {release.pk}"

            assert doi_matches_pattern(
                release.codebase.doi
            ), f"{release.codebase.doi} Codebase DOI doesn't match DataCite pattern!"

            assert doi_matches_pattern(
                release.doi
            ), f"{release.doi} CodebaseRelease DOI doesn't match DataCite pattern!"


def update_metadata_for_all_existing_dois_04():
    print(WELCOME_MESSAGE)

    datacite_api = DataCiteApi()
    all_codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.debug(
        f"Updating metadata for all codebases ({len(all_codebases_with_dois)}) with DOIs and their releases with DOIs. Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )
    input("Press Enter to continue...")

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            f"Processing codebase {i+1}/{len(all_codebases_with_dois)} codebase.pk={codebase.pk}..."
        )

        if DataciteRegistrationLog.is_metadata_stale(codebase):
            logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_codebase(codebase)
            if not ok:
                logger.error(f"Failed to update metadata for codebase {codebase.pk}")
        else:
            logger.debug(f"Metadata for codebase {codebase.pk} is in sync!")

        for j, release in enumerate(codebase.releases.all()):
            logger.debug(
                f"Processing release {j+1}/{codebase.releases.count()} release.pk={release.pk}..."
            )
            if release.peer_reviewed and release.doi:
                if DataciteRegistrationLog.is_metadata_stale(release):
                    logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
                    ok = datacite_api.update_metadata_for_release(release)
                    if not ok:
                        logger.error(
                            f"Failed to update metadata for release {release.pk}"
                        )
                else:
                    logger.debug(f"Metadata for release {release.pk} is in sync!")
            else:
                logger.debug(
                    f'{"Release has no DOI. " if not release.doi else ""}'
                    + f'{"Release is not peer reviewed." if not release.peer_reviewed else ""} Skipping.'
                )

            input("Press Enter to continue...")

    """
    assert correctness
    """
    print(VERIFICATION_MESSAGE)
    if not DRY_RUN:
        logger.debug(f"Checking that Comses metadata is in sync with DataCite:")
        invalid_codebases = []
        invalid_releases = []
        for codebase in all_codebases_with_dois:
            # assert datacite_api.check_metadata(codebase), f"Metadata check not passed for codebase {codebase.pk}"
            if not datacite_api.check_metadata(codebase):
                invalid_codebases.append(codebase.pk)

            for release in codebase.releases.all():
                if release.doi:
                    if not datacite_api.check_metadata(release):
                        invalid_releases.append(release.pk)
                    # assert datacite_api.check_metadata(
                    #     release
                    # ), f"Metadata check not passed for release {release.pk}"

        print(f"Invalid Codebases ({len(invalid_codebases)}): {invalid_codebases}")
        print(f"Invalid Releases ({len(invalid_releases)}): {invalid_releases}")


"""
RECURRENT TASKS
"""


def mint_dois_for_peer_reviewed_releases_without_dois():
    """
    for ALL peer_reviewed releases without DOIs:
    1. Mints DOI for parent codebase, if codebase.doi doesn’t exist.
    2. Mints DOI for release.
    3. Updates metadata for parent codebase and sibling releases
    """

    print(WELCOME_MESSAGE)

    datacite_api = DataCiteApi()

    # CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=True) | Q(doi=""))
    peer_reviewed_releases_without_dois = CodebaseRelease.objects.reviewed_without_doi()

    logger.debug(
        f"Minting DOIs for peer reviewed releases without DOIs  ({len(peer_reviewed_releases_without_dois)}). Query: CodebaseRelease.objects.filter(peer_reviewed=True).filter(Q(doi__isnull=True) | Q(doi="
        ")) ..."
    )
    input("Press Enter to continue...")

    for i, release in enumerate(peer_reviewed_releases_without_dois):
        logger.debug(
            f"Processing release {i+1}/{len(peer_reviewed_releases_without_dois)} release.pk={release.pk}..."
        )
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
                input("Press Enter to continue...")
                continue

            if not DRY_RUN:
                codebase.doi = codebase_doi
                codebase.save()

        """
        Mint DOI for release
        """
        # request to DataCite API
        release_doi = datacite_api.mint_new_doi_for_release(release)
        if not release_doi:
            logger.error(f"Could not mint DOI for release {release.pk}. Skipping.")
            input("Press Enter to continue...")
            continue

        if not DRY_RUN:
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

        input("Press Enter to continue...")


def update_stale_metadata_for_all_codebases_with_dois():
    print(WELCOME_MESSAGE)

    datacite_api = DataCiteApi()
    all_codebases_with_dois = Codebase.objects.exclude(doi__isnull=True)

    logger.debug(
        f"Updating stale metadata for all codebases with DOIs ({len(all_codebases_with_dois)}). Query: Codebase.objects.exclude(doi__isnull=True) ..."
    )
    input("Press Enter to continue...")

    for i, codebase in enumerate(all_codebases_with_dois):
        logger.debug(
            f"Processing Codebase {i+1}/{len(all_codebases_with_dois)}: codebase.pk={codebase.pk} ..."
        )
        if DataciteRegistrationLog.is_metadata_stale(codebase):
            logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_codebase(codebase)
            if not ok:
                logger.error(f"Failed to update metadata for codebase {codebase.pk}")
            else:
                logger.debug(f"Metadata successfully updated.")
        else:
            logger.debug(f"Metadata is in sync. Skipping...")

        input("Press Enter to continue...")

    """
    assert correctness
    """
    print(VERIFICATION_MESSAGE)
    if not DRY_RUN:
        for codebase in all_codebases_with_dois:
            assert datacite_api.check_metadata(
                codebase
            ), f"Metadata check not passed for codebase {codebase.pk}"


def update_stale_metadata_for_all_releases_with_dois():
    print(WELCOME_MESSAGE)

    datacite_api = DataCiteApi()
    all_releases_with_dois = CodebaseRelease.objects.exclude(doi__isnull=True)

    logger.debug(
        f"Updating stale metadata for all releases with DOIs ({len(all_releases_with_dois)}). Query: CodebaseRelease.objects.exclude(doi__isnull=True) ..."
    )
    input("Press Enter to continue...")

    for i, release in enumerate(all_releases_with_dois):
        logger.debug(
            f"Processing Release {i+1}/{len(all_releases_with_dois)}: release.pk={release.pk} ..."
        )
        if DataciteRegistrationLog.is_metadata_stale(release):
            logger.debug(f"Metadata is stale. Updating metadata in DataCite...")
            ok = datacite_api.update_metadata_for_release(release)
            if not ok:
                logger.error(f"Failed to update metadata for release {release.pk}")
            else:
                logger.debug(f"Metadata successfully updated.")
        else:
            logger.debug(f"Metadata is in sync. Skipping...")

        input("Press Enter to continue...")
        continue

    """
    assert correctness
    """
    print(VERIFICATION_MESSAGE)
    if not DRY_RUN:
        for release in all_releases_with_dois:
            assert datacite_api.check_metadata(
                release
            ), f"Metadata check not passed for release {release.pk}"
