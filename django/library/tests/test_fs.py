import io
import os
import shutil
import tarfile
import zipfile

import pathlib

import re
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from core.tests.base import UserFactory
from library.fs import PossibleDirectories, ArchiveExtractor, ListLogger
from library.tests.base import CodebaseFactory
from ..models import CodebaseRelease, Codebase

import logging

logger = logging.getLogger(__name__)


class ArchiveExtractorTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code_files = [(pathlib.Path('src/ex.py'), 'print("Hello world!")'),
                          (pathlib.Path('README.md'), 'Build Instructions\n---------------')]
        super().setUpClass()

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        self.codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = self.codebase_factory.create()
        self.codebase_release = self.codebase.create_release()

    def test_zipfile_saving(self):
        zip_file = io.BytesIO()
        with zipfile.ZipFile(zip_file, 'a') as f:
            for path, content in self.code_files:
                f.writestr(str(path), content)

        archive_name = 'zip.zip'
        zip_file.name = archive_name
        zip_file.seek(0)
        logger = ListLogger.create_bound_list_logger()
        archive_extractor = ArchiveExtractor.from_codebase_release(self.codebase_release, PossibleDirectories.code,
                                                                   logger)
        archive_extractor.process(zip_file)
        events = logger._logger.events
        self.assertEqual(events[0][1]['event'], 'Extracting archive')
        self.assertEqual(events[-1][1]['event'], 'Extracted archive')
