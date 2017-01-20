from django.contrib.auth.models import User
from django.test import TestCase
from django.core.files.base import ContentFile


from ..models import Codebase, CodebaseRelease

import logging

logger = logging.getLogger(__name__)


class BaseModelTestCase(TestCase):

    def setUp(self):
        self.user = self.create_user()

    def create_user(self, username='test_user', password='test', email='testuser@mailinator.com', **kwargs):
        return User.objects.create_user(username=username, password=password, **kwargs)


class CodebaseTest(BaseModelTestCase):

    def setUp(self):
        self.c1 = Codebase.objects.create(title='Test codebase',
                                          description='Test codebase description',
                                          identifier='c1',
                                          submitter=self.create_user()
                                          )

    def test_base_dir(self):
        self.assertEquals(self.c1.base_library_dir, '/library/{0}'.format(self.c1.uuid))
        self.assertEquals(self.c1.base_git_dir, '/repository/{0}'.format(self.c1.uuid))

    def test_make_release(self):
        content = ContentFile('Bunches of test content')
        release = self.c1.make_release(submitted_package=content)
        self.assertEquals(self.c1.latest_version, release)
        self.assertEquals(CodebaseRelease.objects.get(codebase=self.c1, version_number=release.version_number), release)
