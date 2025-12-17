from huey.contrib.djhuey import db_task, on_commit_task
from django.conf import settings

from .models import (
    Codebase,
    CodebaseGitRemote,
    CodebaseRelease,
    GitRefSyncState,
    ImportedReleaseSyncState,
)
from .github_integration import GitHubApi
from .fs import CodebaseGitRepositoryApi

import logging

logger = logging.getLogger(__name__)


@db_task(retries=1, retry_delay=30)
def build_local_git_repo(codebase_id: int):
    """Build or update the local git mirror repository for a codebase without pushing.

    Safe to call multiple times: will append new releases if mirror exists and has prior build state,
    otherwise rebuilds from scratch.
    """
    codebase = Codebase.objects.get(id=codebase_id)
    git_fs_api = CodebaseGitRepositoryApi(codebase)
    # update_or_build handles both first-time build and incremental append
    git_fs_api.update_or_build()


@db_task(retries=1, retry_delay=30)
def append_releases_to_local_git_repo(codebase_id: int):
    """Appends local releases to git mirror."""
    codebase = Codebase.objects.get(id=codebase_id)
    git_fs_api = CodebaseGitRepositoryApi(codebase)
    git_fs_api.append_releases()


@db_task(retries=1, retry_delay=30)
def import_github_release_task(
    codebase_id: int,
    remote_id: int,
    github_release_id: str,
    custom_version: str | None = None,
):
    """Asynchronously import a GitHub release for a given remote using pre-fetched metadata stored on the sync state.

    The sync state should have been created and populated in the API layer.
    On failure, marks the state as ERROR.
    """
    from .github_integration import GitHubReleaseImporter

    remote = CodebaseGitRemote.objects.get(id=remote_id, codebase__id=codebase_id)

    try:
        # sync state must exist already
        sync_state = ImportedReleaseSyncState.objects.filter(
            remote=remote, github_release_id=str(github_release_id)
        ).first()
        if not sync_state:
            raise ValueError("Missing sync state for GitHub release import")

        importer = GitHubReleaseImporter(
            remote=remote, github_release_id=str(github_release_id)
        )
        importer.import_or_reimport(custom_version=custom_version)
    except Exception as e:
        try:
            sync_state = ImportedReleaseSyncState.objects.filter(
                remote=remote, github_release_id=str(github_release_id)
            ).first()
            if sync_state:
                sync_state.log_failure(str(e))
        except Exception:
            logger.exception("Failed to update sync state after import error")
        logger.exception("Failed to import GitHub release asynchronously: %s", e)


@db_task(retries=1, retry_delay=30)
def update_local_repo_release_branch(release_id: int):
    """asynchronous task that updates a SINGLE RELEASE BRANCH with any metadata changes
    that may have occurred.

    This should be called when release metadata has been changed
    """
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.update_release_branch(release)


@db_task(retries=1, retry_delay=30)
def push_all_releases_to_github(codebase_id: int, remote_id: int):
    """Manually push all releases to GitHub for a remote, one-by-one."""
    codebase = Codebase.objects.get(id=codebase_id)
    remote = CodebaseGitRemote.objects.get(id=remote_id, codebase__id=codebase_id)
    git_fs_api = CodebaseGitRepositoryApi(codebase)
    # ensure local repo is up-to-date before pushing
    local_repo = git_fs_api.update_or_build()
    gh_api = GitHubApi(codebase=codebase, local_repo=local_repo, remote=remote)
    # ensure remote exists and persist url
    repo = gh_api.get_or_create_repo()
    if remote.url != repo.html_url:
        remote.url = repo.html_url
        remote.save(update_fields=["url", "last_modified"])

    # push main first if job started
    main_state = GitRefSyncState.for_codebase(codebase)
    if main_state.status == GitRefSyncState.Status.RUNNING:
        try:
            commit_sha, summary = gh_api.push_main(local_repo)
            main_state.record_push_success(commit_sha, summary)
        except Exception as e:
            logger.exception("Failed to push main: %s", e)

    # iterate releases in ascending semver order
    releases = codebase.ordered_releases_list(internal_only=True, asc=True)
    for release in releases:
        state = release.get_or_create_git_ref_sync_state()
        # skip if job not started
        if state.status != GitRefSyncState.Status.RUNNING:
            continue
        try:
            commit_sha, summary = gh_api.push_release(
                local_repo,
                release,
                branch_name=state.branch_name,
                tag_name=state.tag_name,
            )
            # create a release for this tag on GitHub if needed
            gh_api.create_release_for_tag(local_repo, release.version_number)
            state.record_push_success(commit_sha, summary)
        except Exception as e:
            state.log_failure(str(e))
            # continue with remaining releases, keeping per-release isolation
            logger.exception("Failed to push release %s: %s", release.version_number, e)
            continue


@db_task(retries=1, retry_delay=30)
def update_fs_release_metadata(release_id: int):
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    fs_api = release.get_fs_api()
    fs_api.rebuild_metadata()
    # if the release is published and there is a git ref sync state for this release, update it with
    # a new commit
    if (
        release.is_published
        and getattr(release, "git_ref_sync_state", None)
    ):
        update_local_repo_release_branch(release_id)


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
