import re
from github import GithubIntegration, Auth, Github
from github.GithubException import UnknownObjectException
from github.Repository import Repository as GithubRepo
from git import Repo as GitRepo
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Codebase

INSTALLATION_ACCESS_TOKEN_REDIS_KEY = "github_installation_access_token"


class GithubRepoNameValidator:
    @classmethod
    def validate(
        cls,
        repo_name: str,
        username: str | None = None,
        user_access_token: str | None = None,
    ):
        cls._validate_format(repo_name)
        if username and user_access_token:
            cls._check_user_repo_name_unused(repo_name, username, user_access_token)
        elif username:
            raise ValueError("User access token required for user repository")
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
        repo_name: str, username: str, user_access_token: str
    ):
        if username in repo_name:
            raise ValueError(
                f"Repository name cannot contain your username: '{username}'"
            )
        github = Github(user_access_token)
        try:
            github.get_user(username).get_repo(repo_name)
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
        github = Github(GithubApi.get_installation_access_token())
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
        local_repo: GitRepo,
        repo_name: str,
        is_user_repo=False,
        organization_login: str | None = None,
        user_access_token: str | None = None,
        private_repo=False,
    ):
        if is_user_repo:
            raise NotImplementedError("User repositories not yet supported")
        self.private_repo = private_repo
        self.codebase = codebase
        self.local_repo = local_repo
        self.repo_name = repo_name
        self.is_user_repo = is_user_repo
        if is_user_repo and not organization_login:
            raise ValueError("User access token required for user repository")
        if not is_user_repo and not organization_login:
            raise ValueError("Organization login required for org repository")
        self.organization_login = organization_login
        self.user_access_token = user_access_token
        self._github_repo = None

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
        return self.get_installation_access_token()

    @classmethod
    def get_installation_access_token(cls):
        cached_token = cache.get(INSTALLATION_ACCESS_TOKEN_REDIS_KEY)
        if cached_token:
            return cached_token
        return cls.refresh_installation_access_token()

    @staticmethod
    def refresh_installation_access_token():
        """retrieve a new installation access token for the Github app
        and cache it for future use
        """
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
        # just need to link to the app install and it will go to callback with ?code=...
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

    def get_or_create_repo(self) -> GithubRepo:
        """get or create the Github repository for a user or organization"""
        try:
            return self.github_repo
        except:
            if self.is_user_repo:
                self._github_repo = self._create_user_repo()
            else:
                self._github_repo = self._create_org_repo()
        return self._github_repo

    def push(self, local_repo: GitRepo):
        """push the local git repository to the Github repository"""
        if self.is_user_repo:
            raise NotImplementedError("User repositories not yet supported")
        else:
            token = self.installation_access_token
            push_url = f"https://x-access-token:{token}@github.com/{self.github_repo.full_name}.git"
        self._push_to_url(local_repo, push_url)

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
        if self.is_user_repo:
            github = Github(self.user_access_token)
            name = github.get_user().login
            return github.get_repo(f"{name}/{self.repo_name}")
        else:
            github = Github(self.installation_access_token)
            return github.get_repo(f"{self.organization_login}/{self.repo_name}")

    def _create_user_repo(self):
        """create a new repository in the user's account

        this function requires the `repo` scope for the user access token
        """
        token = self.user_access_token
        if not token:
            raise ValueError("User access token required for creating user repository")
        github = Github(token)
        repo = github.get_user().create_repo(
            name=self.repo_name,
            description=self.codebase.description,
            private=self.private_repo,
        )
        return repo

    def _create_org_repo(self):
        """create a new repository in the CoMSES model library organization

        this function requires the `repo` scope for the installation access token
        """
        token = self.installation_access_token
        github = Github(token)
        org = github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME)
        repo = org.create_repo(
            name=self.repo_name,
            description=f"Mirror of {self.codebase.get_absolute_url()}",
            private=self.private_repo,
        )
        return repo

    def _push_to_url(self, local_repo: GitRepo, push_url: str):
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", push_url)
        else:
            local_repo.remotes["origin"].set_url(push_url)
        local_repo.git.push("--set-upstream", "origin", local_repo.active_branch.name)
        local_repo.git.push("--tags")
