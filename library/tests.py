from django.test import TestCase
from django.core.files.base import ContentFile

from .storage import HashStorage

import pathlib
import logging

logger = logging.getLogger(__name__)


# Create your tests here.
class CodebaseStorageTest(TestCase):

    def setUp(self):
        self.root = '/data/repository'
        self.storage = HashStorage(root=self.root)

    def test_hash(self):
        content = 'test content'
        path = self.storage.save('tests/test.txt', ContentFile(content))
        logger.debug("path: %s", path)
        self.assertTrue(pathlib.Path(self.root, path).exists())
        with self.storage.open(path, mode='r') as f:
            self.assertEquals(content, str(f.readline()))

