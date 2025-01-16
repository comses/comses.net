import logging

from core.tests.base import BaseModelTestCase, UserFactory
from .base import (
    CodebaseFactory,
    ReleaseSetup,
)
from library.metadata import CodeMeta

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
