import logging
import pathlib
import random
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
from ..models import Codebase, CodebaseRelease, License, CodeMeta

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
        release = ReleaseSetup.setUpPublishableDraftRelease(self.c1)
        release.validate_publishable()
        release.publish()
        self.assertEquals(self.c1.latest_version, release)
        self.assertEquals(
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
            set(review_draft.programming_languages.all()),
            set(source_release.programming_languages.all()),
        )

        # check file contents
        review_draft_sip_contents = review_draft.get_fs_api().list_sip_contents()
        self.assertEqual(source_sip_contents, review_draft_sip_contents)


class CodeMetaTest(BaseModelTestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)
        
    def test_codemeta_validate(self):
        logger.debug("run some kind of schema validation on the emitted codemeta.json")

    def test_authors(self):
        # create a set of citable Contributors and add them to the release
        # verify that they are included in the correct order in the resulting
        # codemeta object and JSON
        release = self.codebase_release
            # CodebaseRelease has many ReleaseContributors as an ordered set
        number_of_authors = random.randint(5, 8)
        users = []
        for i in range(number_of_authors):
            user = self.user_factory.create(
                username=f"test_author_{i}",
                email=f"test_codemeta{i}@mailinator.com",
                first_name="CodemetaTester",
                last_name=f"Testerson {i}",
            )
            users.append(user)
            release.add_contributor(user, index=i)

        author_list = release.codemeta.metadata['author']

        for i, user in enumerate(users):
            self.assertEqual(user.last_name, author_list[i + 1]['familyName']) #compare last name 
            self.assertEqual(user.first_name, author_list[i + 1]['givenName']) #compare last name
            self.assertEqual(user.email, author_list[i + 1]['email']) #compare last name
            #POSSIBLE FIX: there is a 'i + 1' because the first dictionary in the 'author_list' is an empty dictionary
            

        print("Done with author tests")

    def test_languages(self):

        print("Starting languages test")
        #create a set of languages and add them to the release
        #verify that they are included in the correct order in the resulting codemeta object object and json

        #dont have a language factory so will have to add them manually
        release = self.codebase_release

        num_of_languages = random.randint(1, 5) #pick a random number of languages to add to the codebase release
        language_choices = [
            'Python',
            'C',
            'C++',
            'C#',
            'Java',
            'NetLogo',
        ]

        languages = []
        
    
        for i in range(num_of_languages):
            choice_of_language = language_choices[random.randint(0, len(language_choices) - 1)] #choose random language from list

            languages.append(choice_of_language)
            release.programming_languages.add(choice_of_language)
            
        
        language_list = release.codemeta.metadata['programmingLanguage']

        print(language_list) #tests work when this print statement is uncommented, if commented out, doesnt work
                            #and gives an error with the indexes.

        for i, language in enumerate(languages):
            self.assertEqual(language, language_list[i]['name'])  # compare name of languages

        print("Done with languages test")

    
    def test_keywords(self):

        print("Starting keywords test")

        release = self.codebase_release

        num_of_keywords = random.randint(1,9)
        keywords_choices = [
            'Simulation',
            'Prediction',
            'Analysis',
            'Ecological',
            'Climate Change',
            'Agent-Based',
            'Epidemiological',
            'Computational',
            'Migration',
            'Pattern'
        ]

        keywords = []

        for i in range(num_of_keywords):
            choice_of_keyword = keywords_choices[random.randint(0, len(keywords_choices) - 1)] #choose random keyword
            keywords.append(choice_of_keyword)
            release.codebase.tags.add(choice_of_keyword)

        keyword_list = release.codemeta.metadata['keywords']

        for i, keyword in enumerate(keywords):
            self.assertEqual(keyword, keyword_list[i + 1])


        print("Done with keywords testing")
  

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
