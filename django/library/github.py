from github import GithubIntegration, Auth, Github
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Codebase
from .fs import CodebaseGitRepositoryApi

INSTALLATION_ACCESS_TOKEN_REDIS_KEY = "github_installation_access_token"


class GithubService:
    def __init__(self, codebase: Codebase, debug=False):
        self.debug = debug  # private repos
        self.codebase = codebase
        self.mirror = codebase.git_mirror
        if not self.mirror:
            raise ValueError("Codebase does not have a git mirror")
        self.git_repo_api = CodebaseGitRepositoryApi(codebase)

    @property
    def repo_name(self):
        return self.mirror.repository_name

    @property
    def installation_access_token(self):
        cached_token = cache.get(INSTALLATION_ACCESS_TOKEN_REDIS_KEY)
        if cached_token:
            return cached_token
        return self.refresh_installation_access_token()

    @staticmethod
    def refresh_installation_access_token():
        auth = Auth.AppAuth(
            settings.GITHUB_APP_ID,
            settings.GITHUB_APP_PRIVATE_KEY,
        )
        integration = GithubIntegration(auth=auth)
        installation_auth = integration.get_access_token(
            settings.GITHUB_APP_INSTALLATION_ID
        )
        token = installation_auth.token
        seconds_until_expiration = (
            installation_auth.expires_at - timezone.now()
        ).total_seconds()
        # cache the token for 1 minute less than the expiration time
        cache.set(
            INSTALLATION_ACCESS_TOKEN_REDIS_KEY,
            token,
            seconds_until_expiration - 60,
        )
        return token

    @staticmethod
    def get_user_access_token(code: str):
        """return an access token for the Github user

        this token is used to authenticate requests to the Github API
        to act on behalf of the user on resources they own
        """
        github = Github()
        app = github.get_oauth_application(
            settings.GITHUB_APP_CLIENT_ID,
            settings.GITHUB_APP_CLIENT_SECRET,
        )
        return app.get_access_token(code).token

    def create_user_repository(self, code: str):
        # just need to link to the app install and it will go to callback with ?code=...
        """create a new repository in the user's account

        this function requires the `repo` scope for the user access token
        """
        token = self.get_user_access_token(code)
        github = Github(token)
        github.get_user().create_repo(
            name=self.repo_name,
            description=self.codebase.description,
            private=self.debug,
        )

    def create_org_repository(self):
        """create a new repository in the CoMSES model library organization

        this function requires the `repo` scope for the installation access token
        """
        token = self.installation_access_token
        github = Github(token)
        org = github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME)
        repo = org.create_repo(
            name=self.repo_name,
            private=self.debug,
        )
        return repo

    def mirror_org_repo(self):
        # FIXME: need a way to push stuff if the repo got created but the push failed
        local_repo = self.git_repo_api.build()
        github_repo = self.create_org_repository()
        self.mirror.remote_url = github_repo.html_url

        token = self.installation_access_token
        remote_url = (
            f"https://x-access-token:{token}@github.com/{github_repo.full_name}.git"
        )
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", remote_url)
        else:
            local_repo.remotes["origin"].set_url(remote_url)
        local_repo.git.push("--set-upstream", "origin", local_repo.active_branch.name)
        local_repo.git.push("--tags")
        for tag in local_repo.tags:
            github_repo.create_git_release(
                tag.name,
                name=tag.name,
                message=tag.commit.message,
                draft=False,
                prerelease=False,
            )
        self.mirror.update_remote_releases()
