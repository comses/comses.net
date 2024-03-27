import json
import string
from hypothesis.extra.django import (
    TestCase,
    TransactionTestCase,
    from_model,
    register_field_strategy,
)


from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

from django.contrib.auth.models import User
import jsonschema
from library.tests.base import CodebaseFactory
from library.models import CodeMeta

from typing import List, Tuple
from hypothesis import (
    HealthCheck,
    Verbosity,
    given,
    settings,
    strategies as st,
)

from hypothesis import given
import logging


from hypothesis import settings, Verbosity

from core.tests.base import UserFactory
from library.models import Codebase, CodebaseRelease

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
                "required": ["@type", "givenName", "familyName", "email"],
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
        self.test_counter = 0

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
        # create a set of citable Contributors and add them to the release
        # verify that they are included in the correct order in the resulting
        # codemeta object and JSON
        # CodebaseRelease has many ReleaseContributors as an ordered set

        return submitter, user_factory, codebase_release

    @settings(max_examples=15, verbosity=Verbosity.quiet, deadline=None)
    @given(
        st.lists(
            st.fixed_dictionaries(USER_MAPPING),
            min_size=1,
            max_size=20,
            unique_by=(lambda x: x["username"]),
        )
    )
    def test_authors(self, seed_user_dict_list: List[dict]):
        print(f"Starting authors test {self.test_counter+1}")

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
            release.add_contributor(user, index=i)

        # Function to test: CodeMeta.build(self)
        author_list = release.codemeta.metadata["author"]

        for i, user in enumerate(users):
            self.assertEqual(user.last_name, author_list[i]["familyName"])
            self.assertEqual(user.first_name, author_list[i]["givenName"])
            self.assertEqual(user.email, author_list[i]["email"])

        self.test_counter += 1
        print("Done with authors test")

    @settings(max_examples=15, verbosity=Verbosity.quiet, deadline=None)
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
        print(f"Starting language test {self.test_counter+1}")

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

        self.test_counter += 1
        print("Done with languages test")

    @settings(max_examples=15, verbosity=Verbosity.quiet, deadline=None)
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
        print(f"Starting keywords test {self.test_counter+1}")

        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        for tag in tags:
            release.codebase.tags.add(tag)

        keyword_list = release.codemeta.metadata["keywords"]

        # logger.debug(keyword_list)
        self.assertListEqual(tags, keyword_list)

        self.test_counter += 1
        print("Done with keywords testing")

    @settings(max_examples=15, verbosity=Verbosity.quiet, deadline=None)
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
        print(f"Starting citation test {self.test_counter+1}")

        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        for c in citations:
            release.codemeta.metadata["citation"].append(c)

        citation_list = release.codemeta.metadata["citation"]

        # logger.debug(citation_list)

        self.assertListEqual(citations, citation_list)

        self.test_counter += 1
        print("Done with citations test")

    @settings(max_examples=15, verbosity=Verbosity.quiet, deadline=None)
    @given(st.data())
    def test_codemeta_validate(self, data):
        """
        1. build a codebase with data.draw()
        2. build release with draw()
        3. perform actions (rules?) that change metadata of the release
        4. assert validity of release.codemeta.to_json against SCHEMA

        Add stateful testing!
        https://hypothesis.readthedocs.io/en/latest/stateful.html
        """
        print(f"Starting codemeta validation test {self.test_counter+1}")

        submitter_dict = data.draw(st.fixed_dictionaries(USER_MAPPING))
        submitter, user_factory, release = self.build_release(submitter_dict)

        try:
            jsonschema.validate(release.codemeta.to_json(), schema=CODEMETA_SCHEMA)
        except Exception as e:
            self.fail(f"Validation error: {e}")

        self.test_counter += 1
        print("Done with codemeta validation test")


STATEFUL_STEP_COUNT = 15

"""
This class is used to test whether a random combination of methods that affect CodeMeta will produce a valid codemeta.json
"""


@settings(
    max_examples=3,
    stateful_step_count=STATEFUL_STEP_COUNT,
    verbosity=Verbosity.quiet,
    deadline=None,
    suppress_health_check=[HealthCheck.data_too_large],
)
class CodeMetaValidation(RuleBasedStateMachine):
    print("CodeMetaValidationTester class")

    def __init__(self):
        super().__init__()
        print("CodeMetaValidationTester __init__() - runs once per test!")
        self.contributors = []
        self.contributor_count = 0

    @initialize(data=st.data())
    def init_release(self, data):
        """
        This runs before each test case
        """

        print("@initialize()")

        """
        Generate a pool of unique users dicts
        """
        self.unique_user_dict_pool = data.draw(
            st.lists(
                st.fixed_dictionaries(USER_MAPPING),
                min_size=STATEFUL_STEP_COUNT,
                max_size=STATEFUL_STEP_COUNT,
                unique_by=(lambda x: x["username"]),
            )
        )

        """
        Create one user as submitter
        """
        submitter_dict = self.unique_user_dict_pool.pop()

        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(
            username=submitter_dict["username"],
            email=submitter_dict["email"],
            first_name=submitter_dict["first_name"],
            last_name=submitter_dict["last_name"],
        )

        """
        Create Codebase and CodebaseRelease
        """
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(initialize=False)

        """
        List of contributors
        """

        # print(submitter_dict)

    """
    TODO: add some rules for:
    1. citations
    2. programming languages
    3. keywords
    """

    @rule()
    def add_contributor(self):
        """
        Adds a contributor to the CodebaseRelease
        """

        print("add_contributor()")

        """
        Create one user from the pool data
        """
        user_dict = self.unique_user_dict_pool.pop()
        user = self.user_factory.create(
            username=user_dict["username"],
            email=user_dict["email"],
            first_name=user_dict["first_name"],
            last_name=user_dict["last_name"],
        )

        print(f"Created new user: {user.username}")

        # FUNCTION UNDER TEST
        self.codebase_release.add_contributor(user)

        self.contributors.append(user)

    @invariant()
    def length_agrees(self):
        """
        Length of "author list" in the CodeMeta.build(self.codebase_release)
        should be ALWAYS equal to length of
        self.contributors + 1 (submitter)
        """
        print("length_agrees()")
        # TODO Why self.codebase_release.codemeta.metadata["author"] is cached during tests??
        # author_list = self.codebase_release.codemeta.metadata["author"]
        author_list = CodeMeta.build(self.codebase_release).metadata["author"]

        assert len(author_list) == len(self.contributors) + 1

    @invariant()
    def validate_against_schema(self):
        """
        CodeMeta.build(release).to_json() should ALWAYS validate against CODEMETA_SCHEMA
        """
        print("validate_against_schema()")
        try:
            jsonschema.validate(
                json.loads(CodeMeta.build(self.codebase_release).to_json()),
                schema=CODEMETA_SCHEMA,
            )
            print("codemeta.json is valid!")
        except Exception as e:
            assert False, "CodeMeta validation error: {e}"

    def teardown(self):
        """
        This runs at the end of each test case
        """
        print("teardown()")

        """
        Clean up all created objects
        """
        CodebaseRelease.objects.filter(id=self.codebase_release.id).get().delete()
        Codebase.objects.filter(id=self.codebase.id).get().delete()
        User.objects.filter(id=self.submitter.id).get().delete()

        # delete contributor objects
        for user in self.contributors:
            User.objects.filter(username=user.username).get().delete()


"""
This class is used to run CodeMetaValidation
"""


class StatefulTest(CodeMetaValidation.TestCase, TestCase):

    def __init__(self, *args, **kwargs):
        # Call the __init__ method of the parent classes
        CodeMetaValidation.TestCase.__init__(self, *args, **kwargs)
        TestCase.__init__(self, *args, **kwargs)
        print("StatefulTest.__init__()")
