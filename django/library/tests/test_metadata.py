import logging

from codemeticulous.cff.models import LicenseEnum
from django.test import TestCase
from core.tests.base import BaseModelTestCase, UserFactory
from .base import (
    CodebaseFactory,
    ReleaseSetup,
)
from library.metadata import CodeMeta, ReleaseMetadataConverter

logger = logging.getLogger(__name__)


class CodebaseMetadataTestCase(BaseModelTestCase):

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(
            first_name="Rob", last_name="Submitter"
        )
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.release1 = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        self.release1.publish()

    def test_codebase_codemeta_updates_on_save(self):
        old_codemeta_snapshot = self.codebase.codemeta_snapshot
        self.codebase.description = "Updated codebase description"
        self.codebase.save()
        self.assertNotEqual(old_codemeta_snapshot, self.codebase.codemeta_snapshot)

    def test_codebase_codemeta_snapshot_is_valid(self):
        CodeMeta(**self.codebase.codemeta_snapshot)

    def test_codebase_codemeta_snapshot_has_expected_fields(self):
        snapshot = self.codebase.codemeta_snapshot

        self.assertIn("name", snapshot)
        self.assertIn("@type", snapshot)
        self.assertIn("@id", snapshot)
        self.assertIn("author", snapshot)
        self.assertIn("description", snapshot)

    def test_codebase_datacite_generation(self):
        old_datacite_metadata = self.codebase.datacite_temp.dict(serialize=True)
        self.codebase.description = "new description"
        self.codebase.save()
        new_datacite_metadata = self.codebase.datacite_temp.dict(serialize=True)
        self.assertNotEqual(old_datacite_metadata, new_datacite_metadata)

    def test_release_codemeta_updates_on_save(self):
        old_codemeta_snapshot = self.release1.codemeta_snapshot
        self.release1.release_notes = "Updated release notes"
        self.release1.save()
        self.assertNotEqual(old_codemeta_snapshot, self.release1.codemeta_snapshot)

    def test_release_codemeta_snapshot_is_valid(self):
        CodeMeta(**self.release1.codemeta_snapshot)

    def test_release_codemeta_snapshot_has_expected_fields(self):
        snapshot = self.release1.codemeta_snapshot

        self.assertIn("name", snapshot)
        self.assertIn("@type", snapshot)
        self.assertIn("@id", snapshot)
        self.assertIn("author", snapshot)
        self.assertIn("description", snapshot)

    def test_release_datacite_generation(self):
        old_datacite_metadata = self.release1.datacite_temp.dict(serialize=True)
        self.release1.release_notes = "new release notes"
        self.release1.save()
        new_datacite_metadata = self.release1.datacite_temp.dict(serialize=True)
        self.assertNotEqual(old_datacite_metadata, new_datacite_metadata)

    def test_release_metadata_files_in_package(self):
        # LICENSE, CITATION.cff, codemeta.json
        fs_api = self.release1.get_fs_api()
        sip_contents = fs_api.list_sip_contents()
        files_found = []

        def recurse_contents(contents):
            for item in contents:
                if item["label"].lower() in [
                    "license",
                    "citation.cff",
                    "codemeta.json",
                ]:
                    files_found.append(item["label"])
                if "contents" in item:
                    recurse_contents(item["contents"])

        recurse_contents(sip_contents["contents"])
        self.assertEqual(len(files_found), 3)


class ReleaseMetadataConverterTestCase(TestCase):

    def setUp(self):
        self.minimal_codemeta = {"name": "Test Code"}
        self.minimal_cff = {
            "cff-version": "1.2.0",
            "title": "Test Title",
            "message": "Test Message",
            "authors": [{"name": "Test Author"}],
        }

    def test_extract_license_from_github(self):
        converter = ReleaseMetadataConverter(
            github_repository={"license": {"spdx_id": "MIT"}}
        )
        self.assertEqual(converter._extract_license_from_github(), "MIT")

    def test_extract_license_from_cff(self):
        cff = {**self.minimal_cff, "license": LicenseEnum.GPL_3_0_only}
        converter = ReleaseMetadataConverter(cff=cff)
        self.assertEqual(converter._extract_license_from_cff(), "GPL-3.0-only")

    def test_extract_release_notes_from_codemeta(self):
        codemeta = {**self.minimal_codemeta, "releaseNotes": "From CodeMeta"}
        converter = ReleaseMetadataConverter(codemeta=codemeta)
        self.assertEqual(
            converter._extract_release_notes_from_codemeta(), "From CodeMeta"
        )

    def test_extract_release_notes_from_github(self):
        converter = ReleaseMetadataConverter(github_release={"body": "From GitHub"})
        self.assertEqual(converter._extract_release_notes_from_github(), "From GitHub")

    def test_extract_os_from_codemeta(self):
        codemeta = {**self.minimal_codemeta, "operatingSystem": "Linux"}
        converter = ReleaseMetadataConverter(codemeta=codemeta)
        self.assertEqual(converter._extract_os_from_codemeta(), "linux")

    def test_extract_programming_languages_from_codemeta(self):
        codemeta = {
            **self.minimal_codemeta,
            "programmingLanguage": ["Python", "R"],
        }
        converter = ReleaseMetadataConverter(codemeta=codemeta)
        self.assertEqual(
            converter._extract_programming_languages_from_codemeta(), ["Python", "R"]
        )

    def test_extract_programming_languages_from_github(self):
        converter = ReleaseMetadataConverter(github_repository={"language": "Java"})
        self.assertEqual(
            converter._extract_programming_languages_from_github(), ["Java"]
        )

    def test_extract_platforms_from_codemeta(self):
        codemeta = {
            **self.minimal_codemeta,
            "runtimePlatform": ["Mesa", "NetLogo"],
        }
        converter = ReleaseMetadataConverter(codemeta=codemeta)
        self.assertEqual(
            converter._extract_platforms_from_codemeta(), ["Mesa", "NetLogo"]
        )

    def test_convert_priority(self):
        # test the convert() method's priority logic
        codemeta = {
            **self.minimal_codemeta,
            "releaseNotes": "From CodeMeta",
            "programmingLanguage": ["Python"],
        }
        github_release = {"body": "From GitHub"}
        github_repository = {"license": {"spdx_id": "MIT"}, "language": "Java"}
        cff = {**self.minimal_cff, "license": LicenseEnum.GPL_3_0_only}

        converter = ReleaseMetadataConverter(
            codemeta=codemeta,
            cff=cff,
            github_repository=github_repository,
            github_release=github_release,
        )
        result = converter.convert()
        self.assertEqual(result["license_spdx_id"], "MIT")  # Github > CFF
        self.assertEqual(result["release_notes"], "From CodeMeta")  # CodeMeta > Github
        self.assertEqual(
            result["programming_languages"], ["Python"]
        )  # CodeMeta > Github

    def test_convert_fallback(self):
        """Test the convert() method's fallback logic."""
        github_release = {"body": "From GitHub"}
        github_repository = {"language": "Java"}
        cff = {**self.minimal_cff, "license": LicenseEnum.GPL_3_0_only}

        converter = ReleaseMetadataConverter(
            cff=cff,
            github_repository=github_repository,
            github_release=github_release,
        )
        result = converter.convert()
        self.assertEqual(result["license_spdx_id"], "GPL-3.0-only")
        self.assertEqual(result["release_notes"], "From GitHub")
        self.assertEqual(result["programming_languages"], ["Java"])

    def test_convert_no_sources(self):
        """Test that convert returns gracefully with no sources."""
        converter = ReleaseMetadataConverter()
        result = converter.convert()
        expected = {
            "license_spdx_id": None,
            "release_notes": None,
            "os": "",
            "programming_languages": None,
            "platforms": None,
        }
        self.assertEqual(result, expected)
