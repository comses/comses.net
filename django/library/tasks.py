from huey.contrib.djhuey import db_task, on_commit_task

import logging

logger = logging.getLogger(__name__)


@db_task(retries=1, retry_delay=30)
def update_fs_release_metadata(release_id: int):
    from .models import CodebaseRelease

    release = CodebaseRelease.objects.get(id=release_id)
    fs_api = release.get_fs_api()
    fs_api.rebuild(metadata_only=True)


@on_commit_task()
def schedule_mint_public_doi(release_id: int, dry_run: bool = False):
    """
    Mint a DOI for the given release.

    Args:
        release (CodebaseRelease): The release for which to mint a DOI.
        dry_run (bool, optional): Flag indicating whether the operation should be performed in dry run mode.
            Defaults to False.

    Returns:
        A tuple of DataCiteRegistrationLog or None and a boolean indicating whether the operation was successful
    """
    from .models import CodebaseRelease
    from .doi import DataCiteApi

    release = CodebaseRelease.objects.get(id=release_id)
    return DataCiteApi(dry_run=dry_run).mint_public_doi(release)
