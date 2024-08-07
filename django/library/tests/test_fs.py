from pathlib import Path
import os
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
    FileCategoryDirectories,
    StagingDirectories,
    MessageLevels,
    import_archive,
)
from library.tests.base import CodebaseFactory, TEST_SAMPLES_DIR
from library.models import License


import logging

logger = logging.getLogger(__name__)


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
        self.assertEquals(level, MessageLevels.warning)
        self.assertEquals(len(logs), 2)
        self.assertEqual(
            set(
                fs_api.list(StagingDirectories.originals, FileCategoryDirectories.code)
            ),
            {"nestedcode.zip"},
        )
        # Notice that .DS_Store and .svn folder file are eliminated
        self.assertEqual(
            set(fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)),
            {"src/ex.py", "README.md"},
        )
        fs_api.get_or_create_sip_bag(self.codebase_release.bagit_info)
        fs_api.clear_category(FileCategoryDirectories.code)
        self.assertEqual(
            set(
                fs_api.list(StagingDirectories.originals, FileCategoryDirectories.code)
            ),
            set(),
        )
        self.assertEqual(
            set(fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)),
            set(),
        )

    def test_invalid_zipfile_saving(self):
        archive_name = str(TEST_SAMPLES_DIR / "archives" / "invalid.zip")
        fs_api = self.codebase_release.get_fs_api()
        with open(archive_name, "rb") as f:
            msgs = fs_api.add(
                FileCategoryDirectories.code, content=f, name="invalid.zip"
            )
        logs, level = msgs.serialize()
        self.assertEquals(level, MessageLevels.error)
        self.assertEquals(len(logs), 1)

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
        self.git_mirror = self.codebase.create_git_mirror("animals-model")

    def tearDown(self):
        clear_test_shared_folder(settings.REPOSITORY_ROOT)

    def test_repo_build(self):
        update_release_from_sample(
            self.release_1, self.release_1_dir, version_number="1.0.0"
        )
        self.release_1.publish()
        public_release_count = self.codebase.public_releases().count()
        self.assertEqual(public_release_count, 1)
        api = self.git_mirror.get_repo_api()
        api.build()
        # check that the mirror model is updated and the repo is built
        self.assertIsNotNone(self.git_mirror.last_local_update)
        self.assertEqual(self.git_mirror.local_releases.count(), 1)
        self.assertTrue(os.path.exists(api.repo_dir))
        # check git stuff
        repo = Repo(api.repo_dir)
        self.assertFalse(repo.is_dirty())
        self.assertEqual(sum(1 for _ in repo.iter_commits()), public_release_count)
        self.assertEqual(len(repo.tags), public_release_count)
        # check contents
        self.assertTrue(os.path.exists(api.repo_dir / "codemeta.json"))
        self.assertTrue(os.path.exists(api.repo_dir / "CITATION.cff"))
        self.assertTrue(os.path.exists(api.repo_dir / "LICENSE"))
        fs_api = self.release_1.get_fs_api()
        fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)
        for category in ["code", "data", "docs"]:
            self.assertTrue(
                api.dirs_equal(
                    fs_api.sip_contents_dir / category,
                    api.repo_dir / category,
                )
            )

    def test_repo_append_releases(self):
        update_release_from_sample(
            self.release_1, self.release_1_dir, version_number="1.0.0"
        )
        self.release_1.publish()
        api = self.git_mirror.get_repo_api()
        api.build()
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(
            self.release_2, self.release_2_dir, version_number="2.0.0"
        )
        self.release_2.publish()
        api.append_releases()

        self.assertEqual(self.git_mirror.local_releases.count(), 2)
        # check git stuff
        repo = Repo(api.repo_dir)
        self.assertFalse(repo.is_dirty())
        public_release_count = self.codebase.public_releases().count()
        self.assertEqual(sum(1 for _ in repo.iter_commits()), public_release_count)
        self.assertEqual(len(repo.tags), public_release_count)
        # check contents
        self.assertTrue(os.path.exists(api.repo_dir / "codemeta.json"))
        self.assertTrue(os.path.exists(api.repo_dir / "CITATION.cff"))
        self.assertTrue(os.path.exists(api.repo_dir / "LICENSE"))
        fs_api = self.release_2.get_fs_api()
        fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)
        for category in ["code", "data", "docs"]:
            self.assertTrue(
                api.dirs_equal(
                    fs_api.sip_contents_dir / category,
                    api.repo_dir / category,
                )
            )

    def test_will_not_append_lower_version(self):
        # publish 2.0.0 first and build
        update_release_from_sample(
            self.release_1, self.release_1_dir, version_number="1.0.0"
        )
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(
            self.release_2, self.release_2_dir, version_number="2.0.0"
        )
        self.release_2.publish()
        api = self.git_mirror.get_repo_api()
        api.build()
        # now publish release 1.0.0
        self.release_1.publish()
        self.assertRaises(ValueError, api.append_releases)

    def test_repo_rebuild(self):
        update_release_from_sample(
            self.release_1, self.release_1_dir, version_number="1.0.0"
        )
        self.release_1.publish()
        api = self.git_mirror.get_repo_api()
        api.build()
        self.release_2 = self.codebase.create_release()
        update_release_from_sample(
            self.release_2, self.release_2_dir, version_number="2.0.0"
        )
        self.release_2.publish()
        api.build()

        self.assertEqual(self.git_mirror.local_releases.count(), 2)
        # check git stuff
        repo = Repo(api.repo_dir)
        self.assertFalse(repo.is_dirty())
        public_release_count = self.codebase.public_releases().count()
        self.assertEqual(sum(1 for _ in repo.iter_commits()), public_release_count)
        self.assertEqual(len(repo.tags), public_release_count)
        # check contents
        self.assertTrue(os.path.exists(api.repo_dir / "codemeta.json"))
        self.assertTrue(os.path.exists(api.repo_dir / "CITATION.cff"))
        self.assertTrue(os.path.exists(api.repo_dir / "LICENSE"))
        fs_api = self.release_2.get_fs_api()
        fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)
        for category in ["code", "data", "docs"]:
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
                fs_api.add(FileCategoryDirectories[category], content=f, name=file_name)


def update_release_from_sample(release, sample_dir, version_number):
    release.os = "Linux"
    release.programming_languages.add("Python")
    release.license = License.objects.create(name="MIT")
    release.release_notes = "Initial release"
    release.version_number = version_number
    release.save()
    fs_api = release.get_fs_api()
    for category in ["code", "data", "docs"]:
        upload_category(fs_api, sample_dir, category)
    return release
