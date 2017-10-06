import logging
import pathlib

from django.conf import settings
from django.core.files.base import ContentFile

from .base import BaseModelTestCase
from ..models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


class CodebaseTest(BaseModelTestCase):
    def setUp(self):
        self.c1 = Codebase.objects.create(title='Test codebase',
                                          description='Test codebase description',
                                          identifier='c1',
                                          submitter=self.create_user()
                                          )

    def test_base_dir(self):
        self.assertEquals(self.c1.base_library_dir, pathlib.Path(settings.LIBRARY_ROOT, str(self.c1.uuid)))
        self.assertEquals(self.c1.base_git_dir, pathlib.Path(settings.REPOSITORY_ROOT, str(self.c1.uuid)))

    def test_import_release(self):
        content = ContentFile('Bunches of test content')
        content.name = 'foo.txt'
        release = self.c1.import_release(submitted_package=content)
        release.submitted_package.delete(save=True)
        self.assertEquals(self.c1.latest_version, release)
        self.assertEquals(CodebaseRelease.objects.get(codebase=self.c1, version_number=release.version_number), release)
