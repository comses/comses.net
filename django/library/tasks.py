from huey.contrib.djhuey import db_task

from .models import Codebase, CodebaseRelease

import logging

logger = logging.getLogger(__name__)


@db_task(retries=1, retry_delay=30)
def update_fs_release_metadata(release_id: int):
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    fs_api = release.get_fs_api()
    fs_api.rebuild(metadata_only=True)
