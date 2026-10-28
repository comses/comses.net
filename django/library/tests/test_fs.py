from pathlib import Path
from unittest.mock import PropertyMock, patch
from zipfile import ZipFile
import yaml
from codemeticulous.cff.models import CitationFileFormat
from git import Repo
from django.test import TestCase
from django.conf import settings

from core.tests.base import (
    UserFactory,
    destroy_test_shared_folders,
    initialize_test_shared_folders,
    clear_test_shared_folder,
)
from library.fs import (
    FileCategories,
    StagingDirectories,
    MessageLevels,
    import_archive,
    CodebaseGitRepositoryApi,
)
from library.tests.base import CodebaseFactory, TEST_SAMPLES_DIR
from library.models import CodebaseRelease, ImportedReleaseSyncState, License, GitRefSyncState, ProgrammingLanguage


import logging

logger = logging.getLogger(__name__)

CODEBASE_CONTENT_CATEGORIES = ["code", "data", "docs"]


def setUpModule():
    initialize_test_shared_folders()


class ArchiveExtractorTestCase(TestCase):
    nested_code_folder = TEST_SAMPLES_DIR / "archives" / "nestedcode"

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        self.codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = self.codebase_factory.create()
        self.codebase_release = self.codebase.create_release()

    def test_zipfile_saving(self):
        fs_api = self.codebase_release.get_fs_api()
        msgs = import_archive(
            codebase_release=self.codebase_release,
            nested_code_folder_name=str(self.nested_code_folder),
            fs_api=fs_api,
        )
        logs, level = msgs.serialize()
        self.assertEqual(level, MessageLevels.warning)
        self.assertEqual(len(logs), 2)
        self.assertEqual(
            set(fs_api.list(StagingDirectories.originals, FileCategories.code)),
            {"nestedcode.zip"},
        )
        # Notice that .DS_Store and .svn folder file are eliminated
        self.assertEqual(
            set(fs_api.list(StagingDirectories.sip, FileCategories.code)),
            {"src/ex.py", "README.md"},
        )
        fs_api.get_or_create_sip_bag(self.codebase_release.bagit_info)
        fs_api.clear_category(FileCategories.code)
        self.assertEqual(
            set(fs_api.list(StagingDirectories.originals, FileCategories.code)),
            set(),
        )
        self.assertEqual(
            set(fs_api.list(StagingDirectories.sip, FileCategories.code)),
            set(),
        )

    def test_invalid_zipfile_saving(self):
        archive_name = str(TEST_SAMPLES_DIR / "archives" / "invalid.zip")
        fs_api = self.codebase_release.get_fs_api()
        with open(archive_name, "rb") as f:
            msgs = fs_api.add(FileCategories.code, content=f, name="invalid.zip")
        logs, level = msgs.serialize()
        self.assertEqual(level, MessageLevels.error)
        self.assertEqual(len(logs), 1)

    def test_unpublished_releases_skip_citation_cff(self):
        fs_api = self.codebase_release.get_fs_api()
        for status in CodebaseRelease.Status:
            if status == CodebaseRelease.Status.PUBLISHED:
                continue
            self.codebase_release.status = status
            for force in (False, True):
                with self.subTest(status=status, force=force), self.assertNoLogs("library.fs", level="ERROR"):
                    self.assertFalse(fs_api.create_or_update_citation_cff(force=force))
                    self.assertFalse(fs_api.cff_path.exists())

    def test_review_archive_without_citation_cff(self):
        fs_api = self.codebase_release.get_fs_api()
        with self.assertNoLogs("library.fs", level="ERROR"):
            fs_api.build_review_archive()
        with ZipFile(fs_api.review_archivepath) as archive:
            self.assertIn("codemeta.json", archive.namelist())
            self.assertNotIn("CITATION.cff", archive.namelist())

    def tearDown(self):
        clear_test_shared_folder(settings.REPOSITORY_ROOT)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.nested_code_folder.with_suffix(".zip").unlink(missing_ok=True)


class GitRepoApiTestCase(TestCase):
    model_dir = TEST_SAMPLES_DIR / "releases" / "animals-model"
    release_1_dir = model_dir / "1.0.0"
    release_2_dir = model_dir / "2.0.0"

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        self.codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = self.codebase_factory.create()
        self.release_1 = self.codebase.create_release()

    def tearDown(self):
        clear_test_shared_folder(settings.REPOSITORY_ROOT)

    def _verify_git_repo_status(self, api, release_count):
        """Verify git repo structure and contents are correct."""
        repo = Repo(api.repo_dir)
        self.assertFalse(repo.is_dirty())
        self.assertEqual(sum(1 for _ in repo.iter_commits()), release_count)
        self.assertEqual(len(repo.tags), release_count)
        # check contents
        self.assertTrue((api.repo_dir / "codemeta.json").exists())
        self.assertTrue((api.repo_dir / "CITATION.cff").exists())
        self.assertTrue((api.repo_dir / "LICENSE").exists())

    def test_publish_generates_valid_citation_cff(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.assertFalse(self.release_1.codemeta_snapshot.get("author"))
        with self.assertNoLogs("library.fs", level="ERROR"):
            self.release_1.publish()
        with ZipFile(self.release_1.get_fs_api().archivepath) as archive:
            cff = yaml.safe_load(archive.read("CITATION.cff"))
        CitationFileFormat(**cff)
        self.assertTrue(cff["authors"])
        self.assertEqual(cff["version"], "1.0.0")

    def test_existing_citation_cff_skips_conversion_unless_forced(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_1.publish()
        fs_api = self.release_1.get_fs_api()
        original = fs_api.cff_path.read_text()
        updated = original + "\n# regenerated\n"
        with patch.object(CodebaseRelease, "cff_yaml_str", new_callable=PropertyMock, return_value=updated) as cff:
            self.assertIs(fs_api.create_or_update_citation_cff(), False)
            cff.assert_not_called()
            self.assertEqual(fs_api.cff_path.read_text(), original)
            self.assertIs(fs_api.create_or_update_citation_cff(force=True), True)
            cff.assert_called_once_with()
            self.assertEqual(fs_api.cff_path.read_text(), updated)

    def test_imported_metadata_writers_return_creation_status(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_1.publish()
        self.release_1.imported_release_sync_state = ImportedReleaseSyncState.objects.create(
            github_release_id="12345", tag_name="1.0.0"
        )
        fs_api = self.release_1.get_fs_api()
        for method, path in (
            (fs_api.create_or_update_codemeta, fs_api.codemeta_path),
            (fs_api.create_or_update_citation_cff, fs_api.cff_path),
            (fs_api.create_or_update_license, fs_api.license_path),
        ):
            with self.subTest(file=path.name):
                path.unlink()
                self.assertIs(method(), True)
                self.assertTrue(path.exists())
                self.release_1.imported_release_sync_state.refresh_from_db()
                self.assertEqual(fs_api.manifest.data[path.name], FileCategories.metadata.name)
                self.assertIs(method(), False)
                self.assertIs(method(force=True), True)

    def test_repo_build(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_1.publish()
        public_release_count = self.codebase.releases.public().count()
        self.assertEqual(public_release_count, 1)
        api = CodebaseGitRepositoryApi(self.codebase)
        api.build()
        # check that the git ref sync states are created and the repo is built
        built_releases_count = GitRefSyncState.objects.filter(
            release__codebase=self.codebase, built_commit_sha__isnull=False
        ).count()
        self.assertEqual(built_releases_count, 1)
        self.assertTrue(api.repo_dir.exists())
        self._verify_git_repo_status(api, public_release_count)
        fs_api = self.release_1.get_fs_api()
        for category in CODEBASE_CONTENT_CATEGORIES:
            self.assertTrue(
                api.dirs_equal(
                    fs_api.sip_contents_dir / category,
                    api.repo_dir / category,
                )
            )

    def test_repo_append_releases(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_1.publish()
        api = CodebaseGitRepositoryApi(self.codebase)
        api.build()
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(self.release_2, self.release_2_dir, version_number="2.0.0")
        self.release_2.publish()
        api.append_releases()

        built_releases_count = GitRefSyncState.objects.filter(
            release__codebase=self.codebase, built_commit_sha__isnull=False
        ).count()
        self.assertEqual(built_releases_count, 2)
        public_release_count = self.codebase.releases.public().count()
        self._verify_git_repo_status(api, public_release_count)
        fs_api = self.release_2.get_fs_api()
        for category in CODEBASE_CONTENT_CATEGORIES:
            self.assertTrue(
                api.dirs_equal(
                    fs_api.sip_contents_dir / category,
                    api.repo_dir / category,
                )
            )

    def test_will_not_append_lower_version(self):
        # publish 2.0.0 first and build
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(self.release_2, self.release_2_dir, version_number="2.0.0")
        self.release_2.publish()
        api = CodebaseGitRepositoryApi(self.codebase)
        api.build()
        # now publish release 1.0.0
        self.release_1.publish()
        self.assertRaises(ValueError, api.append_releases)

    def test_repo_rebuild(self):
        update_release_from_sample(self.release_1, self.release_1_dir, version_number="1.0.0")
        self.release_1.publish()
        api = CodebaseGitRepositoryApi(self.codebase)
        api.build()
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(self.release_2, self.release_2_dir, version_number="2.0.0")
        self.release_2.publish()
        api.build()

        built_releases_count = GitRefSyncState.objects.filter(
            release__codebase=self.codebase, built_commit_sha__isnull=False
        ).count()
        self.assertEqual(built_releases_count, 2)
        public_release_count = self.codebase.releases.public().count()
        self._verify_git_repo_status(api, public_release_count)
        fs_api = self.release_2.get_fs_api()
        for category in CODEBASE_CONTENT_CATEGORIES:
            self.assertTrue(
                api.dirs_equal(
                    fs_api.sip_contents_dir / category,
                    api.repo_dir / category,
                )
            )


def tearDownModule():
    destroy_test_shared_folders()


# helpers ================================================


def upload_category(fs_api, release_dir: Path, category: str):
    category_path = release_dir / category
    for filepath in category_path.rglob("*"):
        if filepath.is_file():
            with filepath.open("rb") as f:
                relpath = filepath.relative_to(category_path)
                file_name = str(relpath)
                fs_api.add(FileCategories[category], content=f, name=file_name)


def update_release_from_sample(release, sample_dir, version_number):
    release.os = "Linux"
    python, _created = ProgrammingLanguage.objects.get_or_create_by_name("Python")
    release.programming_languages.add(python)
    release.license = License.objects.create(name="MIT")
    release.release_notes = "Initial release"
    release.version_number = version_number
    release.save()
    fs_api = release.get_fs_api()
    for category in CODEBASE_CONTENT_CATEGORIES:
        upload_category(fs_api, sample_dir, category)
    return release
