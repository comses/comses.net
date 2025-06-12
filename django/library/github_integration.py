import logging
import re
import uuid
from github import GithubIntegration, Auth, Github
from github.GithubException import GithubException, UnknownObjectException
from github.Repository import Repository as GithubRepo
from git import PushInfo, Repo as GitRepo
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .metadata import ReleaseMetadataConverter
from .models import (
    Codebase,
    CodebaseGitRemote,
    CodebaseRelease,
    Contributor,
    License,
    GithubIntegrationAppInstallation,
    ImportedReleasePackage,
)

logger = logging.getLogger(__name__)

INSTALLATION_ACCESS_TOKEN_REDIS_KEY = "github_installation_access_token"


class GitHubRepoValidator:

    def __init__(self, repo_name: str):
        self.repo_name = repo_name

    def validate_format(self):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.repo_name):
            raise ValueError(
                "The repository name can only contain ASCII letters, digits, and the characters ., -, and _"
            )
        if not (1 <= len(self.repo_name) <= 100):
            raise ValueError("Repository name is too long (maximum is 100 characters)")
        if self.repo_name.endswith(".git"):
            raise ValueError("Repository name cannot end with '.git'")
        if "github" in self.repo_name:
            raise ValueError("Repository name cannot contain 'github'")

    def check_org_repo_name_unused(self):
        if settings.GITHUB_MODEL_LIBRARY_ORG_NAME in self.repo_name:
            raise ValueError(
                f"Repository name cannot contain the organization name: '{settings.GITHUB_MODEL_LIBRARY_ORG_NAME}'"
            )
        github = Github(GitHubApi.get_org_installation_access_token())
        full_name = f"{settings.GITHUB_MODEL_LIBRARY_ORG_NAME}/{self.repo_name}"
        try:
            github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME).get_repo(
                self.repo_name
            )
            raise ValueError(
                f"Repository already exists at https://github.com/{full_name}"
            )
        except UnknownObjectException:
            return True

    def get_existing_user_repo_url(
        self, installation: GithubIntegrationAppInstallation
    ):
        token = GitHubApi.get_user_installation_access_token(installation)
        full_name = f"{installation.github_login}/{self.repo_name}"
        github_repo = GitHubApi.get_existing_repo(token, full_name)
        if github_repo.private:
            raise ValueError(
                f"Repository at https://github.com/{full_name} is private. Only public repositories can be synced."
            )
        return github_repo.html_url

    def check_user_repo_empty(self, installation: GithubIntegrationAppInstallation):
        token = GitHubApi.get_user_installation_access_token(installation)
        full_name = f"{installation.github_login}/{self.repo_name}"
        github_repo = GitHubApi.get_existing_repo(
            token,
            full_name,
        )
        if github_repo.private:
            raise ValueError(
                f"Repository at https://github.com/{full_name} is private. Only public repositories can be synced."
            )
        try:
            # this should raise a 404 if the repository is empty
            github_repo.get_contents("")
            raise ValueError(
                f"Repository at https://github.com/{full_name} is not empty"
            )
        except GithubException as e:
            if e.status == 404:
                return True
            raise e


class GitHubApi:
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
            full_name = f"{self.repo_owner}/{self.repo_name}"
            self._github_repo = self.get_existing_repo(
                self.installation_access_token,
                full_name,
            )
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

    def get_or_create_repo(self) -> GithubRepo:
        """get or create the Github repository for a user or organization"""
        try:
            return self.github_repo
        except:
            if self.is_user_repo:
                raise ValueError("User-owned repositories must be created beforehand")
            else:
                self._github_repo = self._create_org_repo()
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

    @staticmethod
    def get_existing_repo(access_token: str, full_name: str) -> GithubRepo:
        """attempt to get an existing repository for the authenticated user or organization"""
        github = Github(access_token)
        try:
            return github.get_repo(full_name)
        except:
            raise ValueError(
                f"Github repository https://github.com/{full_name} does not exist or is inaccessible"
            )

    def _create_org_repo(self):
        """create a new repository in the CoMSES model library organization

        this function requires the `repo` scope for the installation access token
        """
        token = self.installation_access_token
        github = Github(token)
        org = github.get_organization(settings.GITHUB_MODEL_LIBRARY_ORG_NAME)
        repo = org.create_repo(
            name=self.repo_name,
            description=f"Mirror of {self.codebase.permanent_url}",
        )
        return repo

    def _push_to_url(self, local_repo: GitRepo, push_url: str) -> str:
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", push_url)
        else:
            local_repo.remotes["origin"].set_url(push_url)
        # https://gitpython.readthedocs.io/en/stable/reference.html#git.remote.PushInfo
        remote = local_repo.remote(name="origin")
        result_all = remote.push(all=True)
        result_tags = remote.push(tags=True)
        timestamp = f"[{timezone.now().isoformat()}]:\n"
        summaries = []
        success_mask = PushInfo.NEW_HEAD | PushInfo.FAST_FORWARD | PushInfo.UP_TO_DATE
        for info in result_all:
            if info:  # result will be None if the push failed entirely
                if info.flags & success_mask:
                    summaries.append(f"branch ({info.local_ref}): successfully pushed")
                else:
                    summaries.append(
                        f"branch ({info.local_ref}): did not push, likely due to changes in GitHub repository"
                    )
        if not summaries:
            return timestamp + "push failed entirely"
        return timestamp + "\n".join(summaries)


class GitHubReleaseImporter:
    def __init__(self, payload: dict):
        # https://docs.github.com/en/webhooks/webhook-events-and-payloads?actionType=released#release
        github_action = payload.get("action")
        if github_action == "released":
            # release was published, or a pre-release was changed to a release
            self.is_new_github_release = True
        elif github_action == "edited":
            # details of a release, pre-release, or draft were edited
            self.is_new_github_release = False
        else:
            raise ValueError("Unhandled action type")

        self.github_release = payload.get("release")
        self.installation = payload.get("installation")
        self.repository = payload.get("repository")
        if not (self.github_release and self.installation and self.repository):
            raise ValueError("Payload is missing required fields")

        if self.github_release.get("draft") or self.github_release.get("prerelease"):
            raise ValueError("Draft or pre-release, ignoring")

        if self.repository.get("private", False):
            raise ValueError("Private repository, ignoring")

        self.github_release_id = str(self.github_release.get("id"))

        try:
            self.remote = CodebaseGitRemote.objects.get(
                should_import=True,
                owner=self.repository["owner"]["login"],
                repo_name=self.repository["name"],
            )
            self.codebase = self.remote.mirror.codebase
        except CodebaseGitRemote.DoesNotExist:
            raise ValueError("Remote does not exist")

    @property
    def installation_token(self):
        installation = self.codebase.submitter.github_integration_app_installation
        return GitHubApi.get_user_installation_access_token(installation)

    def import_or_reimport(self) -> bool:
        if not self.github_release.get("zipball_url"):
            return self.log_failure("No zipball found in the github release")

        try:
            existing_release = self.codebase.releases.filter(
                codebase=self.codebase,
                imported_release_package__uid=self.github_release_id,
                status__in=[
                    CodebaseRelease.Status.UNPUBLISHED,
                    CodebaseRelease.Status.UNDER_REVIEW,
                ],
            ).first()
            if existing_release:
                return self.reimport_release(existing_release)
            else:
                return self.import_new_release()
        except Exception as e:
            logger.exception(
                f"Error importing GitHub release with id {self.github_release_id}): {e}"
            )
            return self.log_failure("An unexpected error occurred")

    def import_new_release(self) -> bool:
        # make sure the release doesn't already exist as imported release
        if self.codebase.releases.filter(
            imported_release_package__uid=self.github_release_id
        ).exists():
            return self.log_failure("Release already exists")

        # determine version number, make sure it doesn't already exist
        version_number = self.extract_semver(self.github_release.get("tag_name", ""))
        if not version_number:
            version_number = self.extract_semver(self.github_release.get("name", ""))
        if not version_number:
            return self.log_failure(
                "Missing a semantic version number (X.X.X) in the release tag or name"
            )
        if self.codebase.releases.filter(version_number=version_number).exists():
            return self.log_failure(
                f"Release with version {version_number} already exists"
            )

        # create a new imported codebase release
        with transaction.atomic():
            package = ImportedReleasePackage.objects.create(
                uid=self.github_release_id,
                service=ImportedReleasePackage.Services.GITHUB,
                name=self.github_release.get("tag_name"),
                display_name=self.github_release.get("name", ""),
                html_url=self.github_release.get("html_url", ""),
                download_url=self.github_release.get("zipball_url", ""),
                extra_data=self.github_release,
            )
            release = CodebaseRelease.objects.create(
                codebase=self.codebase,
                submitter=self.codebase.submitter,
                status=CodebaseRelease.Status.UNPUBLISHED,
                share_uuid=uuid.uuid4(),
                version_number=version_number,
                imported_release_package=package,
            )
            # add submitter as a release contributor automatically
            contributor, created = Contributor.from_user(self.codebase.submitter)
            release.add_contributor(contributor)

        return self._import_package_and_metadata(release)

    def reimport_release(self, release) -> bool:
        # ignore request if the release package hasn't changed
        # unless the release is newly released on github
        if not self.is_new_github_release:
            if (
                release.imported_release_package.download_url
                == self.github_release.get("zipball_url")
            ):
                return False

        return self._import_package_and_metadata(release)

    def _import_package_and_metadata(self, release) -> bool:
        # import the release package
        fs_api = release.get_fs_api()
        codemeta, cff = fs_api.import_release_package(self.installation_token)

        # extract metadata from the release package and save it to the release
        release_fields = ReleaseMetadataConverter(
            codemeta, cff, self.repository, self.github_release
        ).convert()
        license_spdx_id = release_fields.pop("license_spdx_id", None)
        platforms = release_fields.pop("platforms", [])
        programming_languages = release_fields.pop("programming_languages", [])
        for key, value in release_fields.items():
            setattr(release, key, value)
        license = License.objects.filter(name=license_spdx_id).first()
        if license:
            release.license = license
        if platforms:
            release.platform_tags.add(*platforms)
        if programming_languages:
            release.programming_languages.add(*programming_languages)
        release.save()

        return self.log_success()

    def extract_semver(self, value) -> str | None:
        match = re.search(r"v?(\d+\.\d+\.\d+)", value)
        return match.group(1) if match else None

    def log_failure(self, message: str):
        self._log(
            f"Failed to {'' if self.is_new_github_release else 're-'}import release {self.github_release.get('name')}:\n{message}"
        )
        return False

    def log_success(self):
        self._log(
            f"Successfully {'' if self.is_new_github_release else 're-'}imported release {self.github_release.get('name')}"
        )
        return True

    def _log(self, message: str):
        timestamp = f"[{timezone.now().isoformat()}]:\n"
        self.remote.last_import_log = timestamp + message
        self.remote.save()
