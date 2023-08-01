import logging
import pathlib
import semver
import uuid

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory, BaseModelTestCase
from .base import (
    CodebaseFactory,
    ContributorFactory,
    ReleaseContributorFactory,
)
from ..models import Codebase, CodebaseRelease, License

logger = logging.getLogger(__name__)


class CodebaseTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.c1 = Codebase.objects.create(
            title="Test codebase",
            description="Test codebase description",
            identifier="c1",
            submitter=self.user,
        )

    def test_base_dir(self):
        self.assertEquals(
            self.c1.base_library_dir,
            pathlib.Path(settings.LIBRARY_ROOT, str(self.c1.uuid)),
        )
        self.assertEquals(
            self.c1.base_git_dir,
            pathlib.Path(settings.REPOSITORY_ROOT, str(self.c1.uuid)),
        )

    def test_create_release(self):
        # FIXME: should create a proper codebase release with actual
        # metadata + file payloads
        """
        release = self.c1.create_release(initialize=False, live=True)
        self.assertEquals(self.c1.latest_version, release)
        self.assertEquals(
            CodebaseRelease.objects.get(
                codebase=self.c1, version_number=release.version_number
            ),
            release,
        )
        """
        pass


class CodebaseReleaseTest(BaseModelTestCase):
    def get_perm_str(self, perm_prefix):
        return "{}.{}_{}".format(
            CodebaseRelease._meta.app_label,
            perm_prefix,
            CodebaseRelease._meta.model_name,
        )

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)

    def test_anonymous_user_perms(self):
        anonymous_user = AnonymousUser()
        self.assertFalse(anonymous_user.has_perm(self.get_perm_str("add")))
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("change"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("delete"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            anonymous_user.has_perm(
                self.get_perm_str("view"), obj=self.codebase_release
            )
        )
        self.codebase_release.live = True
        self.codebase_release.save()
        self.assertTrue(
            anonymous_user.has_perm(
                self.get_perm_str("view"), obj=self.codebase_release
            )
        )

    def test_submitter_perms(self):
        submitter = self.submitter
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("change"), obj=self.codebase_release)
        )
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("delete"), obj=self.codebase_release)
        )
        self.assertTrue(
            submitter.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_superuser_perms(self):
        superuser = self.user_factory.create(is_superuser=True)
        self.assertTrue(superuser.has_perm(self.get_perm_str("add")))
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("change"), obj=self.codebase_release)
        )
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("delete"), obj=self.codebase_release)
        )
        self.assertTrue(
            superuser.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_regular_user_perms(self):
        regular_user = self.user_factory.create()
        self.assertTrue(regular_user.has_perm(self.get_perm_str("add")))
        self.assertFalse(
            regular_user.has_perm(
                self.get_perm_str("change"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            regular_user.has_perm(
                self.get_perm_str("delete"), obj=self.codebase_release
            )
        )
        self.assertFalse(
            regular_user.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )
        self.codebase_release.live = True
        self.codebase_release.save()
        self.assertTrue(
            regular_user.has_perm(self.get_perm_str("view"), obj=self.codebase_release)
        )

    def test_version_number_mutation(self):
        other_codebase_release = self.codebase.create_release(initialize=False)
        version_numbers = other_codebase_release.get_allowed_version_numbers()
        self.assertEqual(
            version_numbers,
            set([semver.parse_version_info(vn) for vn in {"1.0.1", "1.1.0", "2.0.0"}]),
        )

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number("1.0.0")

        with self.assertRaises(ValidationError):
            other_codebase_release.set_version_number("foo-1.0.0")

        other_codebase_release.set_version_number("54.2.0")
        self.assertEqual(other_codebase_release.version_number, "54.2.0")

        other_codebase_release.set_version_number("1.0.1")
        self.assertEqual(other_codebase_release.version_number, "1.0.1")

    def test_create_codebase_release_share_uuid(self):
        """Ensure we can create a second codebase release an it hasa different share uuid"""
        self.codebase_release.share_uuid = uuid.uuid4()
        self.codebase_release.save()
        cr = self.codebase.create_release(initialize=False)
        self.assertNotEqual(self.codebase_release.share_uuid, cr.share_uuid)

    def test_metadata_completeness(self):
        # make sure release contributors are empty since we currently automatically add the submitter as an author
        self.codebase_release.contributors.all().delete()
        self.assertFalse(self.codebase_release.contributors.exists())

        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )
        self.codebase_release.os = "Windows"
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        license = License.objects.create(
            name="0BSD", url="https://spdx.org/licenses/0BSD.html"
        )
        self.codebase_release.license = license
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        self.codebase_release.programming_languages.add("Java")
        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )

        release_contributor_factory = ReleaseContributorFactory(self.codebase_release)
        contributor_factory = ContributorFactory(user=self.submitter)
        contributor = contributor_factory.create()
        release_contributor_factory.create(contributor)

        self.assertRaises(
            ValidationError, lambda: self.codebase_release.validate_publishable()
        )
        self.assertTrue(self.codebase_release.validate_metadata())
