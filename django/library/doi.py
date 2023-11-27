from .models import Codebase, CodebaseRelease

import logging
import requests

logger = logging.getLogger(__name__)


def register_peer_reviewed_codebases():
    """
    Identify all codebases that have been peer reviewed, register them with DataCite DOI REST API and save their minted DOI.
    """
    codebase_releases = CodebaseRelease.objects.reviewed_without_doi()
    for release in codebase_releases:
        # do something magical with each release
        logger.debug("Registering codebase release %s with DataCite", release)
        release.codemeta
        # FIXME: register release with DataCite

        # FIXME: on successful registration: notify authors, cc reviews@comses.net or ?
        # FIXME: on failure, log to sentry
    return codebase_releases
