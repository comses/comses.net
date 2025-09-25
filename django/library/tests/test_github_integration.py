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
        mirror = self.codebase.create_git_mirror()
        self.remote = CodebaseGitRemote.objects.create(
            mirror=mirror,
            owner="testuser",
            repo_name="test-repo",
            is_user_repo=True,
            should_import=True,
        )
        self.payload = SAMPLE_PAYLOAD.copy()

    def test_init_success(self):
        # should initialize successfully with a valid payload
        importer = GitHubReleaseImporter(self.payload)
        self.assertEqual(importer.github_release_id, "12345")
        self.assertEqual(importer.codebase, self.codebase)
        self.assertTrue(importer.is_new_github_release)

    def test_init_failures(self):
        # test various invalid payloads that should raise ValueError
        test_cases = {
            "draft": ("release", "draft", True),
            "prerelease": ("release", "prerelease", True),
            "private": ("repository", "private", True),
            "wrong_action": ("action", None, "created"),
            "no_remote": ("repository", "name", "non-existent-repo"),
        }
        for name, (key1, key2, value) in test_cases.items():
            with self.subTest(name=name):
                bad_payload = self.payload.copy()
                if key2:
                    bad_payload[key1] = bad_payload[key1].copy()
                    bad_payload[key1][key2] = value
                else:
                    bad_payload[key1] = value
                with self.assertRaises(ValueError):
                    GitHubReleaseImporter(bad_payload)

    def test_extract_semver(self):
        # test semantic version extraction
        importer = GitHubReleaseImporter(self.payload)
        self.assertEqual(importer.extract_semver("v1.2.3"), "1.2.3")
        self.assertEqual(importer.extract_semver("1.2.3"), "1.2.3")
        self.assertEqual(importer.extract_semver("version 1.2.3-beta"), "1.2.3")
        self.assertIsNone(importer.extract_semver("1.2"))
        self.assertIsNone(importer.extract_semver("invalid-version"))

    @patch("library.models.CodebaseRelease.get_fs_api")
    @patch("library.github_integration.GitHubApi.get_user_installation_access_token")
    def test_import_new_release(self, mock_get_token, mock_get_fs_api):
        # mock token and fs_api calls
        mock_get_token.return_value = "fake-token"
        mock_fs_api = MagicMock()
        mock_fs_api.import_release_package.return_value = ({}, {})  # codemeta, cff
        mock_get_fs_api.return_value = mock_fs_api

        # import a new release
        importer = GitHubReleaseImporter(self.payload)
        success = importer.import_new_release()

        # check that it was successful and objects were created
        self.assertTrue(success)
        self.assertTrue(
            CodebaseRelease.objects.filter(
                codebase=self.codebase, version_number="1.0.0"
            ).exists()
        )
        release = CodebaseRelease.objects.get(version_number="1.0.0")
        self.assertEqual(release.imported_release_package.uid, "12345")
        self.assertEqual(release.submitter, self.codebase.submitter)
        mock_fs_api.import_release_package.assert_called_once()

    @patch("library.models.CodebaseRelease.get_fs_api")
    @patch("library.github_integration.GitHubApi.get_user_installation_access_token")
    def test_reimport_release(self, mock_get_token, mock_get_fs_api):
        # mock token and fs_api calls
        mock_get_token.return_value = "fake-token"
        mock_fs_api = MagicMock()
        mock_fs_api.import_release_package.return_value = ({}, {})  # codemeta, cff
        mock_get_fs_api.return_value = mock_fs_api

        # first, import a new release
        importer = GitHubReleaseImporter(self.payload)
        importer.import_or_reimport()

        self.assertEqual(CodebaseRelease.objects.count(), 1)
        release = CodebaseRelease.objects.first()
        self.assertEqual(
            release.imported_release_package.download_url,
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

        importer2 = GitHubReleaseImporter(reimport_payload)
        success = importer2.import_or_reimport()

        # assert that the re-import was successful and the release was updated
        self.assertTrue(success)
        self.assertEqual(mock_fs_api.import_release_package.call_count, 2)

        release.refresh_from_db()
        self.assertEqual(release.imported_release_package.download_url, new_url)

        self.remote.refresh_from_db()
        self.assertIn("Successfully re-imported", self.remote.last_import_log)

        # release version number should NOT have changed
        self.assertEqual(release.version_number, "1.0.0")

        # re-importing with no change does nothing
        importer3 = GitHubReleaseImporter(reimport_payload)
        success_no_change = importer3.import_or_reimport()
        self.assertFalse(success_no_change)
        # should still be 2, not called again
        self.assertEqual(mock_fs_api.import_release_package.call_count, 2)

        # re-importing a published release does nothing
        release.status = CodebaseRelease.Status.PUBLISHED
        release.save()
        published_reimport_payload = reimport_payload.copy()
        published_reimport_payload["release"][
            "zipball_url"
        ] = "https://another.url/zipball.zip"
        importer4 = GitHubReleaseImporter(published_reimport_payload)
        success_published = importer4.import_or_reimport()
        self.assertFalse(success_published)
        # fs_api should not be called again
        self.assertEqual(mock_fs_api.import_release_package.call_count, 2)
        self.remote.refresh_from_db()
        self.assertIn("Release already exists", self.remote.last_import_log)

        # re-importing an under_review release should work
        release.status = CodebaseRelease.Status.UNDER_REVIEW
        release.save()
        review_reimport_payload = self.payload.copy()
        review_reimport_payload["action"] = "edited"
        review_reimport_payload["release"] = review_reimport_payload["release"].copy()
        review_url = (
            "https://api.github.com/repos/testuser/test-repo/zipball/v1.0.0-review"
        )
        review_reimport_payload["release"]["zipball_url"] = review_url
        importer5 = GitHubReleaseImporter(review_reimport_payload)
        success_review = importer5.import_or_reimport()
        self.assertTrue(success_review)
        self.assertEqual(mock_fs_api.import_release_package.call_count, 3)
        release.refresh_from_db()
        self.assertEqual(release.imported_release_package.download_url, review_url)
