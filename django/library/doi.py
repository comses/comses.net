from .models import Codebase, CodebaseRelease

from django.conf import settings

from datacite import DataCiteRESTClient, schema43
import logging

logger = logging.getLogger(__name__)


def get_datacite_client():
    """
    Get a DataCite REST API client
    """
    return DataCiteRESTClient(
        username=settings.DATACITE_USERNAME,
        password=settings.DATACITE_PASSWORD,
        prefix=settings.DATACITE_PREFIX,
        test_mode=settings.DATACITE_TEST_MODE,
    )


def register_peer_reviewed_codebases():
    """
    Identify all codebases that have been peer reviewed, register them with DataCite DOI REST API and save their minted DOI.
    """
    codebase_releases = CodebaseRelease.objects.reviewed_without_doi()
    datacite_client = get_datacite_client()
    for release in codebase_releases:
        logger.debug("Registering codebase release %s with DataCite", release)
        try:
            json_metadata = release.codemeta.to_json()
            schema43.validate(json_metadata)
            doi = datacite_client.public_doi(json_metadata, url=release.permanent_url)
            logger.debug("minted public DOI: %s", doi)
            release.doi = doi
            release.save()
        except Exception as e:
            logger.error("DataCite error: %s", e)
            # FIXME: on failure, log to something and continue
            # https://github.com/comses/planning/issues/200

    return codebase_releases
