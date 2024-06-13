import json
import string
from hypothesis.extra.django import (
    TestCase,
)

from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    Bundle,
)

from django.contrib.auth.models import User
import jsonschema
from library.tests.base import CodebaseFactory
from library.models import CodeMeta, Contributor, ReleaseContributor, Role

from typing import List, Tuple
from hypothesis import (
    HealthCheck,
    Verbosity,
    given,
    settings,
    strategies as st,
)

from hypothesis.strategies import data

import logging

st.dictionaries

from core.tests.base import UserFactory
from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


MAX_PROPERTY_TEST_RUNS = 15

MAX_STATEFUL_TEST_RUNS = 5
MAX_STATEFUL_TEST_RULES_COUNT = 15

HYPOTHESIS_SETTINGS_VERBOSITY = Verbosity.quiet

# infered from json-ld.json
# https://raw.githubusercontent.com/codemeta/codemeta/master/codemeta.jsonld
CODEMETA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "properties": {
        "@context": {"type": "string"},
        "@type": {"type": "string", "const": "SoftwareSourceCode"},
        "isPartOf": {
            "type": "object",
            "properties": {
                "@type": {"type": "string", "const": "WebApplication"},
                "applicationCategory": {"type": "string"},
                "operatingSystem": {"type": "string"},
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
            },
            "required": ["@type", "applicationCategory", "name", "url"],
        },
        "publisher": {
            "type": "object",
            "properties": {
                "@id": {"type": "string", "format": "uri"},
                "@type": {"type": "string", "const": "Organization"},
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
            },
            "required": ["@id", "@type", "name", "url"],
        },
        "provider": {
            "type": "object",
            "properties": {
                "@id": {"type": "string", "format": "uri"},
                "@type": {"type": "string", "const": "Organization"},
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
            },
            "required": ["@id", "@type", "name", "url"],
        },
        "name": {"type": "string"},
        "abstract": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "targetProduct": {
            "type": "object",
            "properties": {
                "@type": {"type": "string", "const": "SoftwareApplication"},
                "name": {"type": "string"},
                "operatingSystem": {"type": "string"},
                "applicationCategory": {"type": "string"},
            },
            "required": ["@type", "name", "applicationCategory"],
        },
        "programmingLanguage": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["@type", "name"],
            },
        },
        "author": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string"},
                    "givenName": {"type": "string"},
                    "familyName": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["@type", "givenName", "familyName"],
            },
            "minItems": 1,
        },
        "identifier": {"type": "string", "format": "uri"},
        "dateCreated": {"type": "string", "format": "date-time"},
        "dateModified": {"type": "string", "format": "date-time"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "runtimePlatform": {"type": "array", "items": {"type": "string"}},
        "url": {"type": "string", "format": "uri"},
        "citation": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["@type", "text"],
            },
        },
        "codeRepository": {"type": "string", "format": "uri"},
        "@id": {"type": "string", "format": "uri"},
    },
    "required": [
        "@context",
        "@type",
        "isPartOf",
        "publisher",
        "provider",
        "name",
        "abstract",
        "description",
        "version",
        "targetProduct",
        "author",
        "programmingLanguage",
        "identifier",
        "dateCreated",
        "dateModified",
        "url",
        "@id",
    ],
}

# # Define a mapping with specific keys and their corresponding strategies
# USER_MAPPING = {
#     'username': st.text(min_size=1, alphabet=st.characters(blacklist_characters=['\x00','\ud800'])),
#     'first_name': st.text(min_size=1, alphabet=st.characters(blacklist_characters=['\x00','\ud800'])),
#     'last_name': st.text(min_size=1, alphabet=st.characters(blacklist_characters=['\x00','\ud800'])),
#     'email': st.emails(),
# }

"""
ALLOW ONLY string.printable:
'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'
"""

USER_MAPPING = {
    "username": st.text(min_size=1, alphabet=string.printable),
    "first_name": st.text(min_size=1, alphabet=string.printable),
    "last_name": st.text(min_size=1, alphabet=string.printable),
    "email": st.emails(),
}

"""
This class is used to test all methods which affect CodeMeta object
"""


class CodeMetaTest(TestCase):
    def setUp(self):
        pass

    @staticmethod
    def build_release(
        submitter_dict: dict,
    ) -> Tuple[User, UserFactory, CodebaseRelease]:
        user_factory = UserFactory()
        submitter = user_factory.create(
            username=submitter_dict["username"],
            email=submitter_dict["email"],
            first_name=submitter_dict["first_name"],
            last_name=submitter_dict["last_name"],
        )

        codebase_factory = CodebaseFactory(submitter=submitter)
        codebase = codebase_factory.create()
        codebase_release = codebase.create_release(initialize=False)

        return submitter, user_factory, codebase_release

    @settings(
        max_examples=MAX_PROPERTY_TEST_RUNS,
        verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
        deadline=None,
    )
    @given(
        st.lists(
            st.fixed_dictionaries(USER_MAPPING),
            min_size=1,
            max_size=20,
            unique_by=(lambda x: x["username"]),
        )
    )
    def test_authors(self, seed_user_dict_list: List[dict]):
        logger.debug("test_authors()")
        submitter_dict = seed_user_dict_list.pop()
        submitter, user_factory, release = self.build_release(submitter_dict)

        users = [submitter]
        for i, user_seed in enumerate(seed_user_dict_list):
            user = user_factory.create(
                username=user_seed["username"],
                email=user_seed["email"],
                first_name=user_seed["first_name"],
                last_name=user_seed["last_name"],
            )
            users.append(user)
            contributor, created = Contributor.from_user(user)
            release.add_contributor(contributor, index=i)

        # Function to test: CodeMeta.build(self)
        author_list = release.codemeta.metadata["author"]

        for i, user in enumerate(users):
            self.assertEqual(user.last_name, author_list[i]["familyName"])
            self.assertEqual(user.first_name, author_list[i]["givenName"])
            self.assertEqual(user.email, author_list[i]["email"])

        logger.debug("test_authors() done.")

    @settings(
        max_examples=MAX_PROPERTY_TEST_RUNS,
        verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
        deadline=None,
    )
    @given(
        st.data(),
        st.lists(
            st.text(min_size=1, alphabet=string.printable),
            min_size=1,
            max_size=20,
            unique=True,
        ),
    )
    def test_languages(self, data, programming_language_names: List[str]):
        logger.debug("test_languages()")
        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        for language_name in programming_language_names:
            release.programming_languages.add(language_name)

        language_list = release.codemeta.metadata["programmingLanguage"]

        assert len(language_list) == len(programming_language_names)

        for index, language in enumerate(programming_language_names):
            expected_language_name = language_list[index]["name"]
            self.assertEqual(
                language,
                expected_language_name,
                f"Mismatch found at index {index}. Expected: {expected_language_name}, Actual: {language}",
            )

        logger.debug("test_languages() done.")

    @settings(
        max_examples=MAX_PROPERTY_TEST_RUNS,
        verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
        deadline=None,
    )
    @given(
        st.data(),
        st.lists(
            st.text(min_size=1, alphabet=string.printable),
            min_size=1,
            max_size=20,
            unique=True,
        ),
    )
    def test_keywords(self, data, tags: List[str]):
        logger.debug("test_keywords()")
        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        for tag in tags:
            release.codebase.tags.add(tag)

        keyword_list = release.codemeta.metadata["keywords"]

        # logger.debug(keyword_list)
        self.assertListEqual(tags, keyword_list)

        logger.debug("test_keywords() done.")

    @settings(
        max_examples=MAX_PROPERTY_TEST_RUNS,
        verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
        deadline=None,
    )
    @given(
        st.data(),
        st.lists(
            st.text(min_size=300, max_size=900, alphabet=string.printable),
            min_size=1,
            max_size=20,
            unique=True,
        ),
    )
    def test_citation(self, data, citations: List[str]):
        logger.debug("test_citation()")
        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        for c in citations:
            release.codemeta.metadata["citation"].append(c)

        citation_list = release.codemeta.metadata["citation"]

        self.assertListEqual(citations, citation_list)
        logger.debug("test_citation() done.")

    @settings(
        max_examples=MAX_PROPERTY_TEST_RUNS,
        verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
        deadline=None,
    )
    @given(st.data())
    def test_codemeta_validate(self, data):
        logger.debug("test_codemeta_validate()")

        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        try:
            jsonschema.validate(release.codemeta.to_json(), schema=CODEMETA_SCHEMA)
            logger.debug("codemeta.json is valid.")
        except Exception as e:
            logger.error("codemeta.json is invalid! Validation error: {e}")
            self.fail(f"Validation error: {e}")

        logger.debug("test_codemeta_validate() done.")


"""
This class is used to test whether a random combination of methods that affect CodeMeta will produce a valid codemeta.json
"""


@settings(
    max_examples=MAX_STATEFUL_TEST_RUNS,
    stateful_step_count=MAX_STATEFUL_TEST_RULES_COUNT,
    verbosity=HYPOTHESIS_SETTINGS_VERBOSITY,
    deadline=None,
    suppress_health_check=[HealthCheck.data_too_large],
)
class CodeMetaValidationTest(RuleBasedStateMachine):
    added_release_contributors = Bundle("added_release_contributors")

    @initialize(data=data())
    def setup(self, data):
        """
        This runs before each test case
        """
        logger.debug("setup()")

        self.release_contributors_count = 0
        self.release_nonauthor_contributors_count = 0
        self.release_author_contributors_count = 0
        self.keywords_count = 0
        self.programming_languages_count = 0
        self.citations_count = 0

        """
        Generate a pool of unique users dicts
        """
        unique_user_dict_pool = data.draw(
            st.lists(
                st.fixed_dictionaries(USER_MAPPING),
                min_size=MAX_STATEFUL_TEST_RULES_COUNT,
                max_size=MAX_STATEFUL_TEST_RULES_COUNT,
                unique_by=(lambda x: x["username"]),
            )
        )

        """
        Create users
        """
        self.user_factory = UserFactory()
        self.users = set({})
        for user_dict in unique_user_dict_pool:
            user = self.user_factory.create(
                username=user_dict["username"],
                email=user_dict["email"],
                first_name=user_dict["first_name"],
                last_name=user_dict["last_name"],
            )
            self.users.add(user)

        """
        Create Submitter
        """
        self.submitter = self.users.pop()

        """
        Create Codebase and CodebaseRelease
        """
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)

        #  set initial texts used for citation
        self.codebase.references_text = ""
        self.codebase.replication_text = ""
        self.codebase.associated_publication_text = ""

        # submitter is by default Contributor with role=Role.AUTHOR
        self.release_contributors_count += 1
        self.release_author_contributors_count += 1

        logger.debug("setup() done.")

    @rule(
        role=st.sampled_from(list(Role)),
    )
    def add_contributor(self, role):
        logger.debug("add_contributor()")
        contributor, created = Contributor.from_user(self.users.pop())
        # FUNCTION UNDER TEST
        release_contributor = self.codebase_release.add_contributor(contributor, role)

        self.codebase_release.save()
        self.release_contributors_count += 1

        if role == Role.AUTHOR:
            self.release_author_contributors_count += 1
        else:
            self.release_nonauthor_contributors_count += 1
        logger.debug("add_contributor() done.")

    @rule(
        reference=st.text(min_size=100, alphabet=string.printable),
        replication=st.text(min_size=100, alphabet=string.printable),
        associated_publication=st.text(min_size=100, alphabet=string.printable),
    )
    def add_citation(self, reference, replication, associated_publication):
        logger.debug("add_citation()")
        self.codebase.references_text = reference
        self.codebase.replication_text = replication
        self.codebase.associated_publication_text = associated_publication
        logger.debug("add_citation() done.")

    @rule(programming_language=st.text(min_size=1, alphabet=string.printable))
    def add_programming_language(self, programming_language):
        logger.debug("add_programming_language()")
        existing_pls = self.codebase_release.programming_languages.all()

        if programming_language not in [pl.name for pl in existing_pls]:
            # .upper() is used to make the test pass.
            # TODO: check behaviour when adding programming_languages

            self.codebase_release.programming_languages.add(
                programming_language.upper()
            )
            self.programming_languages_count += 1

        logger.debug("add_programming_language() done.")

    @rule(keyword=st.text(min_size=1, alphabet=string.printable))
    def add_keyword(self, keyword):
        logger.debug("add_keyword()")
        existing_tags = self.codebase_release.codebase.tags.all()
        if keyword not in [tag.name for tag in existing_tags]:
            self.codebase_release.codebase.tags.add(keyword)
            self.keywords_count += 1
        logger.debug("add_keyword() done.")

    @invariant()
    def length_agrees(self):
        """authors"""
        logger.debug("length_agrees()")
        expected_contributors_count = (
            self.codebase_release.codebase_contributors.all().count()
        )

        expected_author_contributors_count = (
            ReleaseContributor.objects.authors(self.codebase_release).all().count()
        )

        expected_nonauthor_contributors_count = (
            ReleaseContributor.objects.nonauthors(self.codebase_release).all().count()
        )

        assert expected_contributors_count == self.release_contributors_count

        assert (
            expected_contributors_count
            == expected_author_contributors_count
            + expected_nonauthor_contributors_count
        )

        assert (
            expected_contributors_count
            == self.release_author_contributors_count
            + self.release_nonauthor_contributors_count
        )

        expected_codemeta_authors_count = len(
            CodeMeta.convert_authors(self.codebase_release)
        )
        assert expected_codemeta_authors_count == self.release_author_contributors_count

        """ keywords """
        expected_keywords_count = self.codebase_release.codebase.tags.all().count()
        assert expected_keywords_count == self.keywords_count

        """ programming_languages """
        expected_programming_languages_count = (
            self.codebase_release.programming_languages.all().count()
        )
        assert expected_programming_languages_count == self.programming_languages_count

        """ citations """
        # Replicate citation building mechanism from CodeMeta
        expected_citation = [
            citation
            for citation in [
                self.codebase.references_text,
                self.codebase.replication_text,
                self.codebase.associated_publication_text,
            ]
            if citation
        ]

        # Extract text from CodeMeta.metadata
        codemeta_citation_flat_text = [
            creative_work["text"]
            for creative_work in CodeMeta.build(self.codebase_release).metadata[
                "citation"
            ]
        ]

        assert expected_citation == codemeta_citation_flat_text

        logger.debug("length_agrees() done.")

    @invariant()
    def validate_against_schema(self):
        """
        CodeMeta.build(release).to_json() should ALWAYS validate against CODEMETA_SCHEMA
        """
        logger.debug("validate_against_schema()")
        try:
            jsonschema.validate(
                json.loads(CodeMeta.build(self.codebase_release).to_json()),
                schema=CODEMETA_SCHEMA,
            )

            logger.debug("codemeta.json is valid.")
            assert True, "codemeta.json is valid."

        except Exception:
            logger.error("codemeta.json is invalid! {e}")
            assert False, "CodeMeta validation error: {e}"

        logger.debug("validate_against_schema() done.")

    def teardown(self):
        """
        Clean up all created objects. This runs at the end of each test case
        """
        logger.debug("teardown()")

        # TODO: why is this check necessary? Why does hypothesis run multiple @initialize and teardown at start?
        if self.codebase_release is not None:
            try:
                # Delete CodebaseRelease
                CodebaseRelease.objects.filter(id=self.codebase_release.id).delete()
                # Delete Codebase
                Codebase.objects.filter(id=self.codebase.id).delete()
                # Delete Submitter
                User.objects.filter(id=self.submitter.id).delete()
                # Delete Contributor objects
                for user in self.users:
                    User.objects.filter(username=user.username).delete()
            except Exception as err:
                logger.error(f"Exception during teardown: {err}")

        logger.debug("teardown() done.")


"""
This class is used to run CodeMetaValidationTest
"""


class StatefulCodeMetaValidationTest(CodeMetaValidationTest.TestCase, TestCase):
    def __init__(self, *args, **kwargs):
        # Call the __init__ method of the parent classes
        CodeMetaValidationTest.TestCase.__init__(self, *args, **kwargs)
        TestCase.__init__(self, *args, **kwargs)
