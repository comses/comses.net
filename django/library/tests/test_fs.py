from django.test import TestCase

from core.tests.base import UserFactory
from library.fs import FileCategoryDirectories, ArchiveExtractor, StagingDirectories, MessageLevels
from library.tests.base import CodebaseFactory

import logging

logger = logging.getLogger(__name__)


class ArchiveExtractorTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        self.codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = self.codebase_factory.create()
        self.codebase_release = self.codebase.create_release()

    def test_zipfile_saving(self):
        archive_name = 'library/tests/archives/nestedcode.zip'
        fs_api = self.codebase_release.get_fs_api()
        with open(archive_name, 'rb') as f:
            msgs = fs_api.add(FileCategoryDirectories.code, content=f, name="nestedcode.zip")
        logs, level = msgs.serialize()
        self.assertEquals(level, MessageLevels.info)
        self.assertEquals(len(logs), 0)
        self.assertEqual(set(fs_api.list(StagingDirectories.originals, FileCategoryDirectories.code)),
                         {'nestedcode.zip'})
        self.assertEqual(set(fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)),
                         {'src/ex.py', 'README.md'})
        fs_api.get_or_create_sip_bag(self.codebase_release.bagit_info)
        fs_api.clear_category(FileCategoryDirectories.code)
        self.assertEqual(set(fs_api.list(StagingDirectories.originals, FileCategoryDirectories.code)),
                         set())
        self.assertEqual(set(fs_api.list(StagingDirectories.sip, FileCategoryDirectories.code)),
                         set())

    def test_invalid_zipfile_saving(self):
        archive_name = 'library/tests/archives/invalid.zip'
        fs_api = self.codebase_release.get_fs_api()
        with open(archive_name, 'rb') as f:
            msgs = fs_api.add(FileCategoryDirectories.code, content=f, name="invalid.zip")
        logs, level = msgs.serialize()
        self.assertEquals(level, MessageLevels.error)
        self.assertEquals(len(logs), 1)