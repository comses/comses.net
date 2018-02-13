import logging
import pathlib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory
from .base import BaseModelTestCase, CodebaseFactory
from ..models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


class CodebaseTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.c1 = Codebase.objects.create(title='Test codebase',
                                          description='Test codebase description',
                                          identifier='c1',
                                          submitter=self.user
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


class CodebaseReleaseTest(BaseModelTestCase):
    def get_perm_str(self, perm_prefix):
        return '{}.{}_{}'.format(CodebaseRelease._meta.app_label, perm_prefix,
                                 CodebaseRelease._meta.model_name)

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)

    def test_anonymous_user_perms(self):
        anonymous_user = AnonymousUser()
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str('add')))
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str('change'), obj=self.codebase_release))
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str('delete'), obj=self.codebase_release))
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str('view'), obj=self.codebase_release))
        self.codebase_release.live = True
        self.codebase_release.save()
        self.assertTrue(anonymous_user.has_perm(self.get_perm_str('view'), obj=self.codebase_release))

    def test_submitter_perms(self):
        submitter = self.submitter
        self.assertTrue(submitter.has_perm(self.get_perm_str('change'), obj=self.codebase_release))
        self.assertTrue(submitter.has_perm(self.get_perm_str('delete'), obj=self.codebase_release))
        self.assertTrue(submitter.has_perm(self.get_perm_str('view'), obj=self.codebase_release))

    def test_superuser_perms(self):
        superuser = self.user_factory.create(is_superuser=True)
        self.assertTrue(superuser.has_perm(self.get_perm_str('add')))
        self.assertTrue(superuser.has_perm(self.get_perm_str('change'), obj=self.codebase_release))
        self.assertTrue(superuser.has_perm(self.get_perm_str('delete'), obj=self.codebase_release))
        self.assertTrue(superuser.has_perm(self.get_perm_str('view'), obj=self.codebase_release))

    def test_regular_user_perms(self):
        regular_user = self.user_factory.create()
        self.assertTrue(regular_user.has_perm(self.get_perm_str('add')))
        self.assertFalse(regular_user.has_perm(self.get_perm_str('change'), obj=self.codebase_release))
        self.assertFalse(regular_user.has_perm(self.get_perm_str('delete'), obj=self.codebase_release))
        self.assertFalse(regular_user.has_perm(self.get_perm_str('view'), obj=self.codebase_release))
        self.codebase_release.live = True
        self.codebase_release.save()
        self.assertTrue(regular_user.has_perm(self.get_perm_str('view'), obj=self.codebase_release))

    def test_version_number_mutation(self):
        other_codebase_release = self.codebase.create_release(initialize=False)
        version_numbers = other_codebase_release.get_allowed_version_numbers()
        self.assertEqual(version_numbers, {'1.0.1', '1.1.0', '2.0.0'})

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number('1.0.0')

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number('foo-1.0.0')

        other_codebase_release.set_version_number('54.2.0')
        self.assertEqual(other_codebase_release.version_number, '54.2.0')

        other_codebase_release.set_version_number('1.0.1')
        self.assertEqual(other_codebase_release.version_number,'1.0.1')
