from huey.contrib.djhuey import db_task
from django.conf import settings

from .models import Codebase, CodebaseRelease
from .github_integration import GithubApi
from .fs import CodebaseGitRepositoryApi

import logging

logger = logging.getLogger(__name__)


@db_task(retries=3, retry_delay=30)
def build_and_push_codebase_repo(codebase_id: int, private_repo=False):
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.update_or_build()

    for remote in mirror.remotes.filter(should_push=True):
        gh_api = GithubApi(
            codebase=codebase,
            local_repo=local_repo,
            remote=remote,
        )
        repo = gh_api.get_or_create_repo(private=private_repo)
        remote.url = repo.html_url
        push_summary = gh_api.push(local_repo)
        remote.last_push_log = push_summary
        remote.save()
        gh_api.create_releases(local_repo)


@db_task(retries=3, retry_delay=30)
def add_releases_and_push_codebase_repo(codebase_id: int):
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.append_releases()

    for remote in mirror.remotes.filter(should_push=True):
        gh_api = GithubApi(
            codebase=codebase,
            local_repo=local_repo,
            remote=remote,
        )
        push_summary = gh_api.push(local_repo)
        remote.last_push_log = push_summary
        remote.save()
        gh_api.create_releases(local_repo)


@db_task(retries=3, retry_delay=30)
def update_release_branch_and_push_codebase_repo(release_id: int):
    """asynchronous task that updates a SINGLE RELEASE BRANCH with any metadata changes
    that may have occurred.

    This should be called when release metadata has been changed
    """
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.update_release_branch(release)

    # local_repo will be None if no changes were made
    if local_repo:
        for remote in mirror.remotes.filter(should_push=True):
            gh_api = GithubApi(
                codebase=codebase,
                local_repo=local_repo,
                remote=remote,
            )
            push_summary = gh_api.push(local_repo)
            remote.last_push_log = push_summary
            remote.save()


@db_task(retries=1, retry_delay=30)
def update_fs_release_metadata(release_id: int):
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    fs_api = release.get_fs_api()
    fs_api.rebuild(metadata_only=True)
    # if the release is published and the codebase has a git mirror,
    # update the metadata in the git repository
    if release.is_published and codebase.git_mirror:
        update_release_branch_and_push_codebase_repo(release_id)
