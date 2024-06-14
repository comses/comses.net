from pathlib import Path

from django.test import TestCase

from core.tests.base import (
    UserFactory,
    destroy_test_shared_folders,
    initialize_test_shared_folders,
)
from library.fs import (
    FileCategoryDirectories,
    StagingDirectories,
    MessageLevels,
    import_archive,
)
from library.tests.base import CodebaseFactory


import logging

logger = logging.getLogger(__name__)


def setUpModule():
    initialize_test_shared_folders()


class ArchiveExtractorTestCase(TestCase):
    nested_code_folder = Path("library/tests/archives/nestedcode")

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
        archive_name = "library/tests/archives/invalid.zip"
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


def tearDownModule():
    destroy_test_shared_folders()
