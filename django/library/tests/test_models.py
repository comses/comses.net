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
from ..models import Codebase, CodebaseRelease, Contributor, License, CodeMeta

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
        users = [self.submitter]
        for i in range(number_of_authors):
            user = self.user_factory.create(
                username=f"test_author_{i}",
                email=f"test_codemeta{i}@mailinator.com",
                first_name="CodemetaTester",
                last_name=f"Testerson {i}",
            )
            users.append(user)
            contributor, created = Contributor.from_user(user)
            release.add_contributor(contributor, index=i)

        author_list = release.codemeta.metadata["author"]

        print(author_list)

        for i, user in enumerate(users):
            self.assertEqual(user.last_name, author_list[i]["familyName"])
            self.assertEqual(user.first_name, author_list[i]["givenName"])
            self.assertEqual(user.email, author_list[i]["email"])

        print("Done with author tests")

    def test_languages(self):
        print("Starting languages test")

        release = self.codebase_release

        languages = [
            "Python",
            "C",
            "C++",
            "C#",
            "Java",
            "NetLogo",
        ]

        for language in languages:
            release.programming_languages.add(language)

        language_list = release.codemeta.metadata["programmingLanguage"]

        # logger.debug(language_list)

        for i, language in enumerate(languages):
            self.assertEqual(language, language_list[i]["name"])

        print("Done with languages test")

    def test_keywords(self):
        print("Starting keywords test")

        release = self.codebase_release

        tags = [
            "Simulation",
            "Prediction",
            "Analysis",
            "Ecological",
            "Climate Change",
            "Agent-Based",
            "Epidemiological",
            "Computational",
            "Migration",
            "Pattern",
        ]

        for tag in tags:
            release.codebase.tags.add(tag)

        keyword_list = release.codemeta.metadata["keywords"]

        # logger.debug(keyword_list)

        self.assertListEqual(tags, keyword_list)

        print("Done with keywords testing")

    def test_citation(self):
        print("Starting citations test")

        release = self.codebase_release

        citations = [
            "Smith, John & Doe, Jane. (2018). Understanding the Impact of Climate Change on Urban Infrastructure. In International Conference on Sustainable Urban Development, (pp. 112–128). Elsevier.\n\nJ. Smith and J. Doe, “Urban resilience and climate change: Adaptation strategies for urban areas,” in Proceedings of the Global Conference on Climate Change, pp. 45–60, 2018.",
            "Brown, Samuel & Knight, Teresa. (2015). The Role of Social Media in Modern Political Campaigns. InAnnual Meeting of the Political Science Association, (pp. 75–91). Cambridge University Press.\n\nS. Brown and T. Knight, “Engagement or echo chamber? Social media and political campaigning,” in Journal of Digital Media & Policy, vol. 6, no. 3, pp. 233–248, 2015.",
            "Lee, Ming & Zhang, Wei. (2020). Advances in Quantum Computing: A Survey. In International Symposium on Quantum Technology, (pp. 202–216). IEEE.\n\nM. Lee and W. Zhang, “Quantum computing: From theoretical concepts to practical applications,” in Quantum Information Processing, vol. 19, no. 7, Article 152, 2020.",
            "Garcia, Roberto & Lopez, Maria. (2017). The Evolution of E-commerce: A Comparative Study. In Conference on Digital Business Models, (pp. 134–150). ACM.\n\nR. Garcia and M. Lopez, “E-commerce platforms and the digital economy,” in E-commerce Research, vol. 5, no. 2, pp. 89–104, 2017.",
            "Patel, Anil & Kumar, Vijay. (2019). The Influence of Artificial Intelligence on Healthcare. In International Conference on Medical Informatics, (pp. 88–102). Springer.\n\nA. Patel and V. Kumar, “AI in healthcare: Promises and challenges,” in Health Informatics Journal, vol. 25, no. 3, pp. 590–604, 2019.",
            "Morris, Linda & Thompson, Gary. (2016). Renewable Energy Sources and Their Economic Impact. In Global Summit on Renewable Energy, (pp. 54–69). Oxford University Press.\n\nL. Morris and G. Thompson, “Evaluating the economic benefits of renewable energy,” in Renewable Energy Review, vol. 11, no. 4, pp. 213–229, 2016.",
            "Chen, Xiao & Yang, Jun. (2021). Blockchain Technology in Supply Chain Management: An Overview. In International Conference on Supply Chain Management and Information Systems, (pp. 175–189). IEEE.\n\nX. Chen and J. Yang, “Blockchain and its applications in supply chain management,” in Supply Chain Management: An International Journal, vol. 26, no. 5, pp. 425–439, 2021.",
            "Kim, Soo-Hyun & Park, Ji-Hoon. (2014). The Dynamics of Cultural Globalization and Local Identity. In World Conference on Cultural Studies, (pp. 98–112). Sage Publications.\n\nS.-H. Kim and J.-H. Park, “Cultural globalization and identity dynamics,” in Journal of Cultural Economics, vol. 38, no. 2, pp. 159–174, 2014.",
            "Fernandez, Carlos & Rodriguez, Ana. (2023). Cybersecurity in the Age of IoT: Challenges and Solutions. In International Workshop on Internet of Things Security, (pp. 46–61). Springer.\n\nC. Fernandez and A. Rodriguez, “Securing IoT devices: Trends and challenges,” in IoT Security Journal, vol. 2, no. 1, pp. 22–37, 2023.",
        ]

        for c in citations:
            release.codemeta.metadata["citation"].append(c)

        citation_list = release.codemeta.metadata["citation"]

        # logger.debug(citation_list)

        self.assertListEqual(citations, citation_list)

        print("Done with citations test")


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
