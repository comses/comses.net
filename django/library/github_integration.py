import re
from github import GithubIntegration, Auth, Github
from github.GithubException import UnknownObjectException
from github.Repository import Repository as GithubRepo
from github.AuthenticatedUser import AuthenticatedUser
from git import Repo as GitRepo
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Codebase, CodebaseGitRemote, GithubIntegrationAppInstallation

INSTALLATION_ACCESS_TOKEN_REDIS_KEY = "github_installation_access_token"


class GithubRepoNameValidator:
    @classmethod
    def validate(
        cls,
        repo_name: str,
        installation: GithubIntegrationAppInstallation | None = None,
    ):
        cls._validate_format(repo_name)
        if installation:
            cls._check_user_repo_name_unused(repo_name, installation)
        else:
            cls._check_org_repo_name_unused(repo_name)

    @staticmethod
    def _validate_format(repo_name: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", repo_name):
            raise ValueError(
                "The repository name can only contain ASCII letters, digits, and the characters ., -, and _"
            )
        if not (1 <= len(repo_name) <= 100):
            raise ValueError("Repository name is too long (maximum is 100 characters)")
        if repo_name.endswith(".git"):
            raise ValueError("Repository name cannot end with '.git'")
        if "github" in repo_name:
            raise ValueError("Repository name cannot contain 'github'")

    @staticmethod
    def _check_user_repo_name_unused(
        repo_name: str, installation: GithubIntegrationAppInstallation
    ):
        username = installation.github_login
        if username in repo_name:
            raise ValueError(
                f"Repository name cannot contain your username: '{username}'"
            )
        github = Github(GithubApi.get_user_installation_access_token(installation))
        try:
            github.get_user().get_repo(repo_name)
            raise ValueError(
                f"Repository name already exists at https://github.com/{username}/{repo_name}"
            )
        except UnknownObjectException:
            return True

    @staticmethod
    def _check_org_repo_name_unused(repo_name: str):
        if settings.GITHUB_MODEL_LIBRARY_ORG_NAME in repo_name:
            raise ValueError(
                f"Repository name cannot contain the organization name: '{settings.GITHUB_MODEL_LIBRARY_ORG_NAME}'"
            )
        github = Github(GithubApi.get_org_installation_access_token())
        try:
            github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME).get_repo(
                repo_name
            )
            raise ValueError(
                f"Repository name already exists at https://github.com/{settings.GITHUB_MODEL_LIBRARY_ORG_NAME}/{repo_name}"
            )
        except UnknownObjectException:
            return True


class GithubApi:
    """Functionality for interacting with a remote Github repository
    and Github API
    """

    def __init__(
        self,
        codebase: Codebase,
        remote: CodebaseGitRemote,
        local_repo: GitRepo,
    ):
        self.codebase = codebase
        self.remote = remote
        self.local_repo = local_repo
        self._github_repo = None

    @property
    def repo_owner(self):
        return self.remote.owner

    @property
    def repo_name(self):
        return self.remote.repo_name

    @property
    def is_user_repo(self):
        return self.remote.is_user_repo

    @property
    def github_repo(self) -> GithubRepo:
        if not self._github_repo:
            try:
                self._github_repo = self._get_existing_repo()
            except:
                raise ValueError("Github repository not created yet")
        return self._github_repo

    @property
    def installation_access_token(self):
        if self.is_user_repo:
            return self.get_user_installation_access_token(self.remote.installation)
        return self.get_org_installation_access_token()

    @staticmethod
    def get_user_installation_access_token(
        installation: GithubIntegrationAppInstallation | None,
    ) -> str | None:
        if not installation:
            return None
        auth = Auth.AppAuth(
            settings.GITHUB_INTEGRATION_APP_ID,
            settings.GITHUB_INTEGRATION_APP_PRIVATE_KEY,
        )
        integration = GithubIntegration(auth=auth)
        installation_auth = integration.get_access_token(installation.installation_id)
        return installation_auth.token

    @classmethod
    def get_org_installation_access_token(cls) -> str:
        cached_token = cache.get(INSTALLATION_ACCESS_TOKEN_REDIS_KEY)
        if cached_token:
            return cached_token
        return cls.refresh_org_installation_access_token()

    @staticmethod
    def refresh_org_installation_access_token() -> str:
        """retrieve a new installation access token for the Github app installed
        on the central CoMSES model library organization account and cache it for future use
        """
        auth = Auth.AppAuth(
            settings.GITHUB_INTEGRATION_APP_ID,
            settings.GITHUB_INTEGRATION_APP_PRIVATE_KEY,
        )
        integration = GithubIntegration(auth=auth)
        installation_auth = integration.get_access_token(
            settings.GITHUB_INTEGRATION_APP_INSTALLATION_ID
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

    def get_or_create_repo(self, private=False) -> GithubRepo:
        """get or create the Github repository for a user or organization"""
        try:
            return self.github_repo
        except:
            if self.is_user_repo:
                self._github_repo = self._create_user_repo(private)
            else:
                self._github_repo = self._create_org_repo(private)
        return self._github_repo

    def push(self, local_repo: GitRepo) -> str:
        """push the local git repository to the Github repository"""
        token = self.installation_access_token
        push_url = f"https://x-access-token:{token}@github.com/{self.github_repo.full_name}.git"
        return self._push_to_url(local_repo, push_url)

    def create_releases(self, local_repo: GitRepo):
        """create Github releases for each tag in the local repository that
        does not already have a corresponding release in the remote repository"""
        for tag in local_repo.tags:
            try:
                existing_release = self.github_repo.get_release(tag.name)
            except:
                existing_release = None
            if not existing_release:
                self.github_repo.create_git_release(
                    tag.name,
                    name=tag.name,
                    message=tag.commit.message,
                    draft=False,
                    prerelease=False,
                )

    def _get_existing_repo(self):
        """attempt to get an existing repository for the authenticated user or organization"""
        github = Github(self.installation_access_token)
        return github.get_repo(f"{self.repo_owner}/{self.repo_name}")

    def _create_user_repo(self, private=False):
        """create a new repository in the user's account

        this function requires the `repo` scope for the installation access token
        """
        token = self.installation_access_token
        github = Github(token)
        repo = github.get_user().create_repo(
            name=self.repo_name,
            description=f"Mirror of {self.codebase.permanent_url}",
            private=private,
        )
        return repo

    def _create_org_repo(self, private=False):
        """create a new repository in the CoMSES model library organization

        this function requires the `repo` scope for the installation access token
        """
        token = self.installation_access_token
        github = Github(token)
        org = github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME)
        repo = org.create_repo(
            name=self.repo_name,
            description=f"Mirror of {self.codebase.permanent_url}",
            private=private,
        )
        return repo

    def _push_to_url(self, local_repo: GitRepo, push_url: str) -> str:
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", push_url)
        else:
            local_repo.remotes["origin"].set_url(push_url)
        # https://gitpython.readthedocs.io/en/stable/reference.html#git.remote.PushInfo
        result_all = local_repo.git.push(["--all"])
        result_tags = local_repo.git.push(["--tags"])
        summaries = []
        for result in (result_all, result_tags):
            if result:  # result will be None if the push failed entirely
                for info in result:
                    if info.summary:
                        summaries.append(info.summary)
        if not summaries:
            return "push failed entirely"
        return "\n".join(summaries)
