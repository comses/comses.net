from huey.contrib.djhuey import db_task
from django.conf import settings

from .models import Codebase
from .github import GithubApi
from .fs import CodebaseGitRepositoryApi

import logging

logger = logging.getLogger(__name__)


@db_task(retries=3, retry_delay=30)
def mirror_codebase(codebase_id: int, is_user_repo=False, code=None, debug=False):
    """asynchronous task that mirrors a codebase to a remote Github repository"""
    codebase = Codebase.objects.get(id=codebase_id)
    mirror = codebase.git_mirror
    if not mirror:
        raise ValueError("Codebase does not have a git mirror")
    if is_user_repo:
        if not code:
            raise ValueError("User repo requires a code")
        mirror.user_access_token = GithubApi.get_user_access_token(code)
    else:
        mirror.organization_login = settings.GITHUB_MODEL_LIBRARY_ORG_NAME
        mirror.save()

    git_fs_api = CodebaseGitRepositoryApi(codebase)
    local_repo = git_fs_api.update_or_build()

    gh_api = GithubApi(
        codebase=codebase,
        local_repo=local_repo,
        repo_name=mirror.repository_name,
        is_user_repo=is_user_repo,
        organization_login=mirror.organization_login,
        user_access_token=mirror.user_access_token,
        debug=debug,
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
