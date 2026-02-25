import logging
import pathlib
import semver
import uuid

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory, BaseModelTestCase
from .base import (
    CodebaseFactory,
    ContributorFactory,
    ReleaseContributorFactory,
    ReleaseSetup,
)
from ..models import (
    ProgrammingLanguage,
    ReleaseLanguage,
    Codebase,
    CodebaseRelease,
    License,
)

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
        self.assertEqual(
            self.c1.base_library_dir,
            pathlib.Path(settings.LIBRARY_ROOT, str(self.c1.uuid)),
        )
        self.assertEqual(
            self.c1.base_git_dir,
            pathlib.Path(settings.REPOSITORY_ROOT, str(self.c1.uuid)),
        )

    def test_create_release(self):
        release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        release.validate_publishable()
        release.publish()
        self.assertEqual(self.c1.latest_version, release)
        self.assertEqual(
            CodebaseRelease.objects.get(
                codebase=self.c1, version_number=release.version_number
            ),
            release,
        )
        fs_api = release.get_fs_api()
        # check that at least something exists for code/docs
        sip_contents = fs_api.list_sip_contents()
        contents = {
            item["label"]: item.get("contents", []) for item in sip_contents["contents"]
        }
        for category in ["code", "docs"]:
            self.assertIn(category, contents)
            self.assertTrue(contents[category])

    def test_create_review_draft_from_release(self):
        source_release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        source_release.refresh_from_db()
        source_release.publish()
        source_sip_contents = source_release.get_fs_api().list_sip_contents()
        review_draft = self.c1.create_review_draft_from_release(source_release)
        # check metadata
        self.assertEqual(
            review_draft.release_notes.rendered, source_release.release_notes.rendered
        )
        self.assertEqual(review_draft.os, source_release.os)
        self.assertEqual(review_draft.output_data_url, source_release.output_data_url)
        self.assertEqual(review_draft.license, source_release.license)
        self.assertEqual(
            set(review_draft.contributors.all()), set(source_release.contributors.all())
        )
        self.assertEqual(
            set(review_draft.platform_tags.all()),
            set(source_release.platform_tags.all()),
        )
        self.assertEqual(
            set(review_draft.release_languages.all()),
            set(source_release.release_languages.all()),
        )
        self.assertEqual(
            set(ReleaseSetup.PROGRAMMING_LANGUAGES),
            set(source_release.programming_languages.values_list("name", flat=True)),
        )
        self.assertEqual(
            set(ReleaseSetup.PROGRAMMING_LANGUAGES),
            set(review_draft.programming_languages.values_list("name", flat=True)),
        )

        self.assertIsNotNone(source_release.codemeta_snapshot)
        self.assertIsNotNone(source_release.codemeta)

        # check file contents
        draft_sip_contents = review_draft.get_fs_api().list_sip_contents()
        logger.info("source sip contents: %s", source_sip_contents)
        logger.info("draft sip contents: %s", draft_sip_contents)
        # FIXME: basic assertEqual won't work for a newly created review draft
        # from a published release which generates a LICENSE, CITATION.cff, and codemeta.json
        # self.assertEqual(source_sip_contents, review_draft_sip_contents)


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
        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
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
        self.codebase_release.status = CodebaseRelease.Status.PUBLISHED
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
        """Ensure we can create a second codebase release and it has a different share uuid"""
        self.codebase_release.share_uuid = uuid.uuid4()
        self.codebase_release.save()
        cr = self.codebase.create_release(initialize=False)
        self.assertNotEqual(self.codebase_release.share_uuid, cr.share_uuid)

    def test_citation_author_ordering(self):
        release_contributor_factory = ReleaseContributorFactory(self.codebase_release)
        contributor_factory = ContributorFactory(user=self.submitter)
        release_contributors = []
        for contributor in contributor_factory.create_unique_contributors(10):
            # create a release contributor with the same index as the contributor
            # to ensure that the ordering is correct
            release_contributors.append(
                release_contributor_factory.create(contributor, randomize_role=True)
            )
            logger.debug(
                "XXX: created release contributor [%s] with roles: %s",
                release_contributors[-1].contributor,
                release_contributors[-1].roles,
            )
        # check that ordering is correct
        for crc, rc in zip(
            self.codebase_release.citable_release_contributors, release_contributors
        ):
            self.assertEqual(crc.contributor, rc.contributor)
            self.assertEqual(crc.index, rc.index)
            self.assertEqual(crc.roles, rc.roles)

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

        java, _created = ProgrammingLanguage.objects.get_or_create(name="Java")
        ReleaseLanguage.objects.create(
            programming_language=java,
            release=self.codebase_release,
            version="8",
        )
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
