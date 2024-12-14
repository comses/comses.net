from huey.contrib.djhuey import db_task
from django.conf import settings

from .models import Codebase, CodebaseRelease
from .github_integration import GithubApi
from .fs import CodebaseGitRepositoryApi

import logging

logger = logging.getLogger(__name__)


@db_task(retries=3, retry_delay=30)
def mirror_codebase(codebase_id: int, private_repo=False):
    """asynchronous task that mirrors a codebase to a remote Github repository"""
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")
    mirror.organization_login = settings.GITHUB_MODEL_LIBRARY_ORG_NAME
    mirror.save()

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.update_or_build()

    gh_api = GithubApi(
        codebase=codebase,
        local_repo=local_repo,
        repo_name=mirror.repository_name,
        is_user_repo=False,
        organization_login=mirror.organization_login,
        user_access_token=mirror.user_access_token,
        private_repo=private_repo,
    )
    repo = gh_api.get_or_create_repo()
    mirror.remote_url = repo.html_url
    gh_api.push(local_repo)
    gh_api.create_releases(local_repo)
    mirror.update_remote_releases()


@db_task(retries=3, retry_delay=30)
def update_mirrored_codebase(codebase_id: int):
    """asynchronous task that updates a mirrored codebase by pushing new releases to Github"""
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")
    if not mirror.remote_url:
        raise ValueError("Codebase git mirror does not have a remote url")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.append_releases()
    gh_api = GithubApi(
        codebase=codebase,
        local_repo=local_repo,
        repo_name=mirror.repository_name,
        is_user_repo=bool(mirror.user_access_token),
        organization_login=mirror.organization_login,
        user_access_token=mirror.user_access_token,
    )
    gh_api.push(local_repo)
    gh_api.create_releases(local_repo)
    mirror.update_remote_releases()


@db_task(retries=3, retry_delay=30)
def update_mirrored_release_metadata(release_id: int):
    """asynchronous task that updates a SINGLE RELEASE BRANCH with metadata changes
    if codemeta.json has changed.

    This should be called when release metadata has been changed
    """
    release = CodebaseRelease.objects.get(id=release_id)
    codebase = release.codebase
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")
    if not mirror.remote_url:
        raise ValueError("Codebase git mirror does not have a remote url")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    if git_fs_api.is_release_codemeta_stale(release):
        local_repo = git_fs_api.update_release_branch(release)
        gh_api = GithubApi(
            codebase=codebase,
            local_repo=local_repo,
            repo_name=mirror.repository_name,
            is_user_repo=bool(mirror.user_access_token),
            organization_login=mirror.organization_login,
            user_access_token=mirror.user_access_token,
        )
        gh_api.push(local_repo)
        mirror.update_remote_releases()


@db_task(retries=3, retry_delay=30)
def update_mirrored_codebase_metadata(codebase_id: int):
    """asynchronous task that updates ALL release branches for a codebase with
    metadata changes if codemeta.json has changed.

    This should be called when the parent codebase metadata has changed
    """
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")
    if not mirror.remote_url:
        raise ValueError("Codebase git mirror does not have a remote url")

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    for release in codebase.releases.all():
        if git_fs_api.is_release_codemeta_stale(release):
            local_repo = git_fs_api.update_release_branch(release)
    gh_api = GithubApi(
        codebase=codebase,
        local_repo=local_repo,
        repo_name=mirror.repository_name,
        is_user_repo=bool(mirror.user_access_token),
        organization_login=mirror.organization_login,
        user_access_token=mirror.user_access_token,
    )
    gh_api.push(local_repo)
    mirror.update_remote_releases()
