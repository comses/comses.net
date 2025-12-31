from unittest.mock import patch, MagicMock
from django.test import TestCase

from core.tests.base import UserFactory
from library.github_integration import (
    GitHubRepoValidator,
    GitHubReleaseImporter,
)
from library.models import (
    CodebaseGitRemote,
    GithubIntegrationAppInstallation,
    CodebaseRelease,
    ImportedReleaseSyncState,
)
from library.tests.base import CodebaseFactory

SAMPLE_PAYLOAD = {
    "action": "released",
    "release": {
        "id": 12345,
        "tag_name": "v1.0.0",
        "name": "Version 1.0.0",
        "body": "Initial release",
        "draft": False,
        "prerelease": False,
        "zipball_url": "https://api.github.com/repos/testuser/test-repo/zipball/v1.0.0",
        "html_url": "https://github.com/testuser/test-repo/releases/tag/v1.0.0",
    },
    "repository": {
        "name": "test-repo",
        "owner": {"login": "testuser"},
        "private": False,
    },
    "installation": {"id": 54321},
}


class GitHubRepoValidatorTests(TestCase):
    def setUp(self):
        # set up a user and installation for testing validator methods
        self.user = UserFactory().create()
        self.installation = GithubIntegrationAppInstallation.objects.create(
            user=self.user,
            github_login="testuser",
            installation_id=1,
            github_user_id=123,
        )

    def test_validate_format(self):
        # test valid repo names
        for name in ["repo", "repo-1", "repo.1", "my_repo"]:
            with self.subTest(name=name):
                validator = GitHubRepoValidator(name)
                self.assertIsNone(validator.validate_format())

        # test invalid repo names
        for name in [
            "repo with space",
            "repo!",
            "a" * 101,
            "repo.git",
            "contains-github",
        ]:
            with self.subTest(name=name):
                validator = GitHubRepoValidator(name)
                with self.assertRaises(ValueError):
                    validator.validate_format()


class GitHubReleaseImporterTests(TestCase):
    def setUp(self):
        # set up a user, codebase, and remote for importing releases
        self.user = UserFactory().create()
        self.installation = GithubIntegrationAppInstallation.objects.create(
            user=self.user,
            github_login="testuser",
            installation_id=54321,
            github_user_id=123,
        )
        self.codebase = CodebaseFactory(submitter=self.user).create()
        self.remote = CodebaseGitRemote.objects.create(
            codebase=self.codebase,
            owner="testuser",
            repo_name="test-repo",
            is_user_repo=True,
            is_active=True,
        )
        self.payload = SAMPLE_PAYLOAD.copy()
        # create sync state from payload
        self.sync_state = ImportedReleaseSyncState.for_github_release(
            self.remote, self.payload["release"]
        )

    def test_init_success(self):
        # should initialize successfully with a valid remote and release id
        importer = GitHubReleaseImporter(self.remote, "12345")
        self.assertEqual(importer.github_release_id, "12345")
        self.assertEqual(importer.codebase, self.codebase)

    def test_init_failures(self):
        # test various invalid scenarios that should raise ValueError
        # missing sync state
        with self.assertRaises(ValueError):
            GitHubReleaseImporter(self.remote, "99999")
        
        # sync state without download_url
        bad_sync_state = ImportedReleaseSyncState.objects.create(
            remote=self.remote,
            github_release_id="88888",
            download_url="",  # empty download url
        )
        with self.assertRaises(ValueError):
            GitHubReleaseImporter(self.remote, "88888")

    def test_extract_semver(self):
        # test semantic version extraction
        importer = GitHubReleaseImporter(self.remote, "12345")
        self.assertEqual(importer.extract_semver("v1.2.3"), "1.2.3")
        self.assertEqual(importer.extract_semver("1.2.3"), "1.2.3")
        self.assertEqual(importer.extract_semver("version 1.2.3-beta"), "1.2.3")
        self.assertIsNone(importer.extract_semver("1.2"))
        self.assertIsNone(importer.extract_semver("invalid-version"))

    @patch("library.github_integration.GitHubApi.get_repo_raw_for_remote")
    @patch("library.models.CodebaseRelease.get_fs_api")
    @patch("library.github_integration.GitHubApi.get_user_installation_access_token")
    def test_import_new_release(self, mock_get_token, mock_get_fs_api, mock_get_repo):
        # mock token and fs_api calls
        mock_get_token.return_value = "fake-token"
        mock_get_repo.return_value = {"name": "test-repo", "full_name": "testuser/test-repo"}
        mock_fs_api = MagicMock()
        mock_fs_api.import_release_package.return_value = ({}, {})  # codemeta, cff
        mock_get_fs_api.return_value = mock_fs_api

        # create sync state first
        ImportedReleaseSyncState.for_github_release(self.remote, self.payload["release"])

        # import a new release
        importer = GitHubReleaseImporter(self.remote, "12345")
        success = importer.import_new_release()

        # check that it was successful and objects were created
        self.assertTrue(success)
        self.assertTrue(
            CodebaseRelease.objects.filter(
                codebase=self.codebase, version_number="1.0.0"
            ).exists()
        )
        release = CodebaseRelease.objects.get(version_number="1.0.0")
        self.assertEqual(release.imported_release_sync_state.github_release_id, "12345")
        self.assertEqual(release.submitter, self.codebase.submitter)
        mock_fs_api.import_release_package.assert_called_once()

    @patch("library.github_integration.GitHubApi.get_release_raw_for_remote")
    @patch("library.github_integration.GitHubApi.get_repo_raw_for_remote")
    @patch("library.models.CodebaseRelease.get_fs_api")
    @patch("library.github_integration.GitHubApi.get_user_installation_access_token")
    def test_reimport_release(self, mock_get_token, mock_get_fs_api, mock_get_repo, mock_get_release):
        # mock token and fs_api calls
        mock_get_token.return_value = "fake-token"
        mock_get_repo.return_value = {"name": "test-repo", "full_name": "testuser/test-repo"}
        mock_fs_api = MagicMock()
        mock_fs_api.import_release_package.return_value = ({}, {})  # codemeta, cff
        mock_get_fs_api.return_value = mock_fs_api

        # create sync state first
        sync_state = ImportedReleaseSyncState.for_github_release(
            self.remote, self.payload["release"]
        )
        
        # first, import a new release
        importer = GitHubReleaseImporter(self.remote, "12345")
        importer.import_or_reimport()

        self.assertEqual(CodebaseRelease.objects.count(), 1)
        release = CodebaseRelease.objects.first()
        self.assertEqual(
            release.imported_release_sync_state.download_url,
            "https://api.github.com/repos/testuser/test-repo/zipball/v1.0.0",
        )

        # now, create a new importer with an updated payload for an "edited" event
        reimport_payload = self.payload.copy()
        reimport_payload["action"] = "edited"
        reimport_payload["release"] = reimport_payload["release"].copy()
        new_url = (
            "https://api.github.com/repos/testuser/test-repo/zipball/v1.0.0-updated"
        )
        reimport_payload["release"]["zipball_url"] = new_url
        # mock get_release_raw_for_remote to return the updated payload
        mock_get_release.return_value = reimport_payload["release"]

        importer2 = GitHubReleaseImporter(self.remote, "12345")
        success = importer2.import_or_reimport()

        # assert that the re-import was successful and the release was updated
        self.assertTrue(success)
        self.assertEqual(mock_fs_api.import_release_package.call_count, 2)

        release.refresh_from_db()
        self.assertEqual(release.imported_release_sync_state.download_url, new_url)

        self.remote.refresh_from_db()

        # release version number should NOT have changed
        self.assertEqual(release.version_number, "1.0.0")


