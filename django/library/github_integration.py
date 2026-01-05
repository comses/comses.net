import logging
import re
import uuid
from datetime import datetime, timezone
from github.GithubException import GithubException, UnknownObjectException
from github.Repository import Repository as GithubRepo
from git import PushInfo, Repo as GitRepo
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from github import GithubIntegration, Auth, Github
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .metadata import ReleaseMetadataConverter
from django.forms.models import model_to_dict
from .models import (
    Codebase,
    CodebaseGitRemote,
    CodebaseRelease,
    Contributor,
    ImportedReleaseSyncState,
    License,
    GithubIntegrationAppInstallation,
)
from taggit.models import Tag
from .serializers import ImportedReleaseSyncStateSerializer
from .fs import CodebaseGitRepositoryApi

logger = logging.getLogger(__name__)

INSTALLATION_ACCESS_TOKEN_REDIS_KEY = "github_installation_access_token"


def get_github_installation_status(user):
    """
    Get GitHub installation status for a user.
    Returns dict with github_account, connect_url, and installation_url.
    """
    installation_url = None
    social_account = user.member_profile.get_social_account("github")
    if social_account:
        github_account = {
            "id": social_account.uid,
            "username": social_account.extra_data.get("login"),
            "profile_url": social_account.get_profile_url(),
        }
    else:
        github_account = None

    if github_account:
        installation_url = f"https://github.com/apps/{slugify(settings.GITHUB_INTEGRATION_APP_NAME)}/installations/new/permissions?target_id={github_account['id']}"
        installation = getattr(user, "github_integration_app_installation", None)
        if installation:
            github_account["installation_id"] = installation.installation_id

    return {
        "github_account": github_account,
        "connect_url": reverse("socialaccount_connections"),
        "installation_url": installation_url,
    }


class GitHubRepoValidator:

    def __init__(self, repo_name: str):
        self.repo_name = repo_name

    def validate_format(self):
        """validate repository name format to match GitHub rules"""
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

    def get_url_for_connectable_user_repo(self, installation: GithubIntegrationAppInstallation, is_preexisting: bool) -> str:
        """validate that a repository exists, is public, and the app has been granted access to it.
        If the repository is not pre-existing, it must be empty.

        returns the HTML URL of the repository if it is valid, otherwise raises an error
        """
        token = GitHubApi.get_user_installation_access_token(installation)
        full_name = f"{installation.github_login}/{self.repo_name}"
        github_repo = GitHubApi.get_existing_repo(token, full_name)
        if github_repo.private:
            raise ValueError(
                f"Repository at https://github.com/{full_name} is private. Only public repositories can be synced."
            )
        self._check_installation_access(installation)
        if not is_preexisting:
            try:
                # this should raise a 404 if the repository is empty
                github_repo.get_contents("")
                raise ValueError(
                    f"Repository at https://github.com/{full_name} is not empty"
                )
            except GithubException as e:
                if e.status == 404:
                    return github_repo.html_url
                raise e
        return github_repo.html_url

    def _check_installation_access(self, installation: GithubIntegrationAppInstallation) -> None:
        """check that the GitHub app installation has access to the repository"""
        auth = Auth.AppAuth(
            settings.GITHUB_INTEGRATION_APP_ID,
            settings.GITHUB_INTEGRATION_APP_PRIVATE_KEY,
        )
        integration = GithubIntegration(auth=auth)
        try:
            # try to get the installation for this specific repository
            # if the installation has access, this will succeed
            integration.get_repo_installation(installation.github_login, self.repo_name)
        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"The CoMSES Integration GitHub app does not have access to the repository at https://github.com/{installation.github_login}/{self.repo_name}. "
                    f"Use the 'Manage permissions' link above to grant access to this repository (or all repositories)."
                )


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
    def get_access_token_for_remote(remote: CodebaseGitRemote) -> str | None:
        """Return an installation access token appropriate for the given remote."""
        if remote.is_user_repo:
            return GitHubApi.get_user_installation_access_token(
                getattr(remote, "installation", None)
            )
        return GitHubApi.get_org_installation_access_token()

    @staticmethod
    def get_release_raw_for_remote(
        remote: CodebaseGitRemote, github_release_id: str | int
    ) -> dict:
        """Fetch a GitHub release raw dict for owner/repo of the remote."""
        token = GitHubApi.get_access_token_for_remote(remote)
        if not token:
            raise ValueError("Unable to acquire installation token")
        gh = Github(token)
        full_name = f"{remote.owner}/{remote.repo_name}"
        repo = gh.get_repo(full_name)
        gh_release = repo.get_release(int(github_release_id))
        return getattr(gh_release, "raw_data", {}) or {}

    @staticmethod
    def get_repo_raw_for_remote(remote: CodebaseGitRemote) -> dict:
        """Fetch a GitHub repository raw dict for owner/repo of the remote."""
        token = GitHubApi.get_access_token_for_remote(remote)
        if not token:
            raise ValueError("Unable to acquire installation token")
        gh = Github(token)
        full_name = f"{remote.owner}/{remote.repo_name}"
        repo = gh.get_repo(full_name)
        return getattr(repo, "raw_data", {}) or {}

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

    @staticmethod
    def get_existing_repo(access_token: str, full_name: str) -> GithubRepo:
        """attempt to get an existing repository for the authenticated user or organization"""
        github = Github(access_token)
        try:
            return github.get_repo(full_name)
        except:
            raise ValueError(
                f"Github repository https://github.com/{full_name} does not exist or is private"
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

    def push_release(
        self,
        local_repo: GitRepo,
        release: CodebaseRelease,
        branch_name: str | None = None,
        tag_name: str | None = None,
    ) -> tuple[str, str]:
        """push only a single release branch and its tag to the remote.

        returns (pushed_commit_sha, summary_str)
        """
        token = self.installation_access_token
        push_url = f"https://x-access-token:{token}@github.com/{self.github_repo.full_name}.git"
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", push_url)
        else:
            local_repo.remotes["origin"].set_url(push_url)
        remote = local_repo.remote(name="origin")

        # determine refs to push
        branch_name = branch_name or (
            f"{CodebaseGitRepositoryApi.RELEASE_BRANCH_PREFIX}{release.version_number}"
        )
        tag_name = tag_name or release.version_number
        repo = local_repo
        try:
            release_branch = repo.heads[branch_name]
        except Exception:
            raise ValueError(f"missing local branch for release: {branch_name}")
        try:
            tag_ref = next((t for t in repo.tags if t.name == tag_name), None)
        except Exception:
            tag_ref = None

        # push refs
        summaries: list[str] = []
        success_mask = PushInfo.NEW_HEAD | PushInfo.FAST_FORWARD | PushInfo.UP_TO_DATE

        def _summarize(push_results, label_prefix: str):
            for info in push_results:
                if info:
                    if info.flags & success_mask:
                        summaries.append(f"{label_prefix}: successfully pushed")
                    else:
                        summaries.append(f"{label_prefix}: did not push")

        # push release branch
        _summarize(remote.push(branch_name), f"branch ({branch_name})")
        # push tag (exactly one) but skip logging until gitpython flag behavior is clearer
        if tag_ref:
            refspec = f"refs/tags/{tag_name}:refs/tags/{tag_name}"
            remote.push(refspec)
        else:
            summaries.append(f"tag ({tag_name}): not found locally")
        timestamp = f"[{timezone.now().isoformat()}]:\n"
        if not summaries:
            summaries.append("no refs pushed")
        return (release_branch.commit.hexsha, timestamp + "\n".join(summaries))

    def push_main(self, local_repo: GitRepo) -> tuple[str, str]:
        """push the main branch to the remote if it exists locally"""
        token = self.installation_access_token
        push_url = f"https://x-access-token:{token}@github.com/{self.github_repo.full_name}.git"
        if "origin" not in local_repo.remotes:
            local_repo.create_remote("origin", push_url)
        else:
            local_repo.remotes["origin"].set_url(push_url)
        remote = local_repo.remote(name="origin")
        repo = local_repo
        try:
            _ = repo.heads[CodebaseGitRepositoryApi.DEFAULT_BRANCH_NAME]
        except Exception:
            return  ("", f"[{timezone.now().isoformat()}]: main not found locally")
        success_mask = PushInfo.NEW_HEAD | PushInfo.FAST_FORWARD | PushInfo.UP_TO_DATE
        summaries: list[str] = []
        for info in remote.push(CodebaseGitRepositoryApi.DEFAULT_BRANCH_NAME):
            if info:
                if info.flags & success_mask:
                    summaries.append("main: successfully pushed")
                else:
                    summaries.append("main: did not push")
        if not summaries:
            summaries.append("main: no refs pushed")
        commit_sha = repo.heads[CodebaseGitRepositoryApi.DEFAULT_BRANCH_NAME].commit.hexsha
        return (commit_sha, f"[{timezone.now().isoformat()}]:\n" + "\n".join(summaries))

    def create_release_for_tag(self, local_repo: GitRepo, tag_name: str):
        """create a GitHub release for a single tag if it does not already exist"""
        try:
            self.github_repo.get_release(tag_name)
            return  # already exists
        except Exception:
            pass
        # try to pull a commit message from local tag for description
        try:
            tag = next((t for t in local_repo.tags if t.name == tag_name), None)
            message = tag.commit.message if tag else ""
        except Exception:
            message = ""
        self.github_repo.create_git_release(
            tag_name,
            name=tag_name,
            message=message or "",
            draft=False,
            prerelease=False,
        )


def list_github_releases_for_remote(remote: CodebaseGitRemote) -> list[dict]:
    """list releases from the connected GitHub repository for the given remote

    returns a list of minimal release dicts with keys: id, name, tag_name, html_url,
    zipball_url, draft, prerelease, created_at, published_at

    includes a `created_by_integration` flag when the release was created (pushed) by the integration app
    """
    # select appropriate installation token (user vs org)
    if remote.is_user_repo:
        token = GitHubApi.get_user_installation_access_token(
            getattr(remote, "installation", None)
        )
    else:
        token = GitHubApi.get_org_installation_access_token()

    if not token:
        return []

    full_name = f"{remote.owner}/{remote.repo_name}"
    gh = Github(token)
    repo = gh.get_repo(full_name)
    releases = repo.get_releases()

    results: list[dict] = []
    for r in releases:
        raw = getattr(r, "raw_data", {}) or {}
        release_id = str(raw.get("id") or getattr(r, "id", ""))
        tag = (
            raw.get("tag_name")
            or getattr(r, "tag_name", "")
            or getattr(r, "tag_name", "")
        )
        name = (
            raw.get("name") or getattr(r, "title", None) or getattr(r, "name", "") or ""
        )
        html_url = raw.get("html_url") or getattr(r, "html_url", "")
        zipball_url = raw.get("zipball_url") or getattr(r, "zipball_url", "")
        created_at = raw.get("created_at") or getattr(r, "created_at", None)
        published_at = raw.get("published_at") or getattr(r, "published_at", None)
        version = extract_semver(tag or name or "")
        has_semver = bool(version)
        data = {
            "id": release_id,
            "name": name,
            "tag_name": tag,
            "html_url": html_url,
            "zipball_url": zipball_url,
            "draft": bool(raw.get("draft", getattr(r, "draft", False))),
            "prerelease": bool(raw.get("prerelease", getattr(r, "prerelease", False))),
            "created_at": created_at,
            "published_at": published_at,
            "has_semantic_versioning": has_semver,
            "version": version or "",
        }
        # annotate whether this release has already been imported for this remote
        imported_state = (
            ImportedReleaseSyncState.objects.filter(
                remote=remote, github_release_id=release_id
            )
            .order_by("-last_modified")
            .first()
        )
        # create or update ImportedReleaseSyncState jobs for user-created releases
        # only update pending (not started) jobs
        # this is the single point at which we create ImportedReleaseSyncStates
        if _is_release_created_by_integration(raw, remote):
            data["created_by_integration"] = True
        else:
            try:
                if imported_state is None or (
                    imported_state.status == ImportedReleaseSyncState.Status.PENDING
                ):
                    imported_state = ImportedReleaseSyncState.for_github_release(
                        remote, raw
                    )
            except Exception as e:
                logger.warning(
                    "failed to upsert imported sync state for %s: %s", release_id, e
                )
        if imported_state:
            data["imported_sync_state"] = ImportedReleaseSyncStateSerializer(
                imported_state
            ).data

        results.append(data)

    # order by published_at
    results.sort(
        key=lambda d: datetime.fromisoformat(str(d.get("published_at")).replace("Z", "+00:00"))
        if d.get("published_at")
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return results


def _is_release_created_by_integration(
    gh_release_raw: dict, remote: CodebaseGitRemote
) -> bool:
    """skip releases created by the integration app"""
    try:
        author_login = gh_release_raw.get("author", {}).get("login", "").lower()
        if slugify(settings.GITHUB_INTEGRATION_APP_NAME) in author_login:
            return True
    except Exception:
        return False
    return False


def extract_semver(value) -> str | None:
    """extract semantic version (X.Y.Z) from a string, tolerant to a leading 'v'

    keep this shared between importer and listing so behavior is consistent.
    """
    if not isinstance(value, str):
        return None
    if len(value) > 1024:  # prevent expensive/malicious inputs
        return None
    match = re.search(r"v?(\d+\.\d+\.\d+)", value)
    return match.group(1) if match else None


class GitHubReleaseImporter:
    def __init__(self, remote: CodebaseGitRemote, github_release_id: str | int):
        """Initialize the importer with the remote and GitHub release id.

        The GitHub release metadata must already be cached on an ImportedReleaseSyncState
        created beforehand
        """
        self.remote = remote
        self.codebase = remote.codebase
        self.github_release_id = str(github_release_id)
        # load cached release metadata from sync state created earlier
        self.sync_state = ImportedReleaseSyncState.objects.filter(
            remote=self.remote, github_release_id=self.github_release_id
        ).first()
        if not self.sync_state:
            raise ValueError(
                "Missing ImportedReleaseSyncState: sync state must be created beforehand"
            )
        self._reimporting = False

        if not self.sync_state.download_url:
            raise ValueError("No zipball found in the github release")

    @property
    def installation_token(self):
        installation = self.codebase.submitter.github_integration_app_installation
        return GitHubApi.get_user_installation_access_token(installation)

    def import_or_reimport(self, custom_version: str | None = None) -> bool:

        try:
            # find any existing release tied to this GitHub release
            existing_release = self.codebase.releases.filter(
                codebase=self.codebase,
                imported_release_sync_state__github_release_id=self.github_release_id,
            ).first()
            if existing_release:
                if existing_release.status in [
                    CodebaseRelease.Status.UNPUBLISHED,
                    CodebaseRelease.Status.UNDER_REVIEW,
                    CodebaseRelease.Status.DRAFT,
                ]:
                    # reimport if editable
                    self._reimporting = True
                    return self.reimport_release(existing_release)
                else:
                    # error if not editable
                    raise ValueError("Published releases cannot be reimported")
            else:
                # otherwise import as a brand new release
                return self.import_new_release(custom_version=custom_version)
        except Exception as e:
            logger.exception(
                f"Error importing GitHub release with id {self.github_release_id}): {e}"
            )
            return self.log_failure("An unexpected error occurred")

    def import_new_release(self, custom_version: str | None = None) -> bool:
        # make sure the release doesn't already exist as imported release
        if self.codebase.releases.filter(
            imported_release_sync_state__github_release_id=self.github_release_id
        ).exists():
            return self.log_failure("Release already exists")

        # determine version number, make sure it doesn't already exist
        version_number = self.extract_semver(self.sync_state.tag_name or "")
        if not version_number:
            version_number = self.extract_semver(self.sync_state.display_name or "")
        if not version_number and custom_version:
            version_number = custom_version
        if not version_number:
            return self.log_failure(
                "Missing a semantic version number (X.X.X) in the release tag or name"
            )
        if self.codebase.releases.filter(version_number=version_number).exists():
            return self.log_failure(
                f"Release with version {version_number} already exists"
            )

        # create a new imported codebase release and link to existing sync state
        with transaction.atomic():
            release = CodebaseRelease.objects.create(
                codebase=self.codebase,
                submitter=self.codebase.submitter,
                status=CodebaseRelease.Status.UNPUBLISHED,
                share_uuid=uuid.uuid4(),
                version_number=version_number,
                imported_release_sync_state=self.sync_state,
            )
            # add submitter as a release contributor automatically
            contributor, created = Contributor.from_user(self.codebase.submitter)
            release.add_contributor(contributor)

        return self._import_package_and_metadata(release)

    def reimport_release(self, release) -> bool:
        # refresh cached metadata
        gh_release_raw = GitHubApi.get_release_raw_for_remote(
            self.remote, self.github_release_id
        )
        # the same download url indicates nothing actually changed, skip import
        if self.sync_state.download_url == gh_release_raw.get("zipball_url"):
            return self.log_success("Attempted reimport, no changes detected")
        self.sync_state = ImportedReleaseSyncState.for_github_release(
            self.remote, gh_release_raw
        )
        return self._import_package_and_metadata(release)

    def _resolve_tags(self, tag_names: list[str]) -> list:
        """
        Resolve a list of tag names to a list of Tag objects or strings
        if the tag does not exist
        """
        resolved_tags = []
        for tag_name in tag_names:
            tag = Tag.objects.filter(name__iexact=tag_name).first()
            if tag:
                resolved_tags.append(tag)
            else:
                resolved_tags.append(tag_name)
        return resolved_tags

    def _import_package_and_metadata(self, release) -> bool:
        # import the release package
        fs_api = release.get_fs_api()
        codemeta, cff = fs_api.import_release_package(self.installation_token)

        # extract metadata from the release package and save it to the release
        gh_repo_raw = GitHubApi.get_repo_raw_for_remote(self.remote)
        release_fields = ReleaseMetadataConverter(
            codemeta, cff, gh_repo_raw, self.sync_state.extra_data or {}
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
            release.platform_tags.add(*self._resolve_tags(platforms))
        if programming_languages:
            release.programming_languages.add(
                *self._resolve_tags(programming_languages)
            )
        release.save()

        return self.log_success()

    def extract_semver(self, value) -> str | None:
        return extract_semver(value)

    def log_failure(self, message: str):
        self.sync_state.log_failure(message)
        return False

    def log_success(self, message: str | None = None):
        display = self.sync_state.display_name or self.sync_state.tag_name
        if not message:
            message = f"Successfully {'re-' if self._reimporting else ''}imported release {display}"
        self.sync_state.log_success(message)
        return True
