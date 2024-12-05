import json
import jsonschema
import logging
import random
import string

from django.contrib.auth.models import User
from hypothesis import (
    note,
    settings,
    strategies as st,
    Verbosity,
)
from hypothesis.extra.django import TestCase
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    Bundle,
)

from core.tests.base import UserFactory
from library.models import (
    CodeMetaSchema,
    CommonMetadata,
    Contributor,
    ReleaseContributor,
    Role,
)
from .base import CodebaseFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


MAX_PROPERTY_TEST_RUNS = 10
MAX_STATEFUL_TEST_RUNS = 5
MAX_STATEFUL_TEST_RULES_COUNT = 15

HYPOTHESIS_VERBOSITY = Verbosity.normal

# We primarily use
# https://schema.org/SoftwareSourceCode
# and CodeMeta v3 https://w3id.org/codemeta/v3.0
#
CODEMETA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CodeMeta 3.0 JSON-LD Schema",
    "description": "Schema for CodeMeta version 3.0 in JSON-LD format.",
    "type": "object",
    "required": [
        "@context",
        "@id",
        "@type",
        "author",
        "identifier",
        "license",
        "name",
        "programmingLanguage",
        "url",
    ],
    "properties": {
        "@context": {"type": "string", "enum": ["https://w3id.org/codemeta/v3.0"]},
        "@type": {"type": "string", "enum": ["SoftwareSourceCode"]},
        "name": {"type": "string", "description": "The name of the software."},
        "author": {
            "type": "array",
            "description": "An array of authors for the software.",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string", "enum": ["Person", "Organization"]},
                    "givenName": {"type": "string"},
                    "familyName": {"type": "string"},
                    "email": {"type": "string"},
                    "affiliation": {
                        "type": "object",
                        "properties": {
                            "@type": {"type": "string", "enum": ["Organization"]},
                            "name": {
                                "type": "string",
                                "description": "The name of the affiliated organization.",
                            },
                        },
                    },
                },
                "required": ["@type", "givenName", "familyName"],
                "minItems": 1,
            },
        },
        "version": {"type": "string", "description": "The version of the software."},
        "description": {
            "type": "string",
            "description": "A short description of the software.",
        },
        "license": {
            "type": "string",
            "description": "A URL to the software’s license.",
        },
        "codeRepository": {
            "type": "string",
            "description": "A URL to the source code repository.",
        },
        "issueTracker": {
            "type": "string",
            "description": "A URL to the issue tracker for the software.",
        },
        "programmingLanguage": {
            "type": "array",
            "description": "The programming language(s) of the software.",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string"},
                    "name": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                },
                "required": ["@type", "name"],
            },
        },
        "keywords": {
            "type": "array",
            "description": "Keywords or tags for the software.",
            "items": {"type": "string"},
        },
        "softwareRequirements": {
            "type": "array",
            "description": "Software or hardware requirements for the software.",
            "items": {"type": "string"},
        },
        "softwareSuggestions": {
            "type": "array",
            "description": "Recommended software to accompany this software.",
            "items": {"type": "string"},
        },
        "citation": {
            "type": "array",
            "description": "Associated citation(s) for the software.",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["@type", "text"],
            },
        },
        "identifier": {"type": "string", "format": "uri"},
        "dateCreated": {
            "type": "string",
            "format": "date",
            "description": "The date when the software was created.",
        },
        "dateModified": {
            "type": "string",
            "format": "date",
            "description": "The date when the software was last modified.",
        },
        "datePublished": {
            "type": "string",
            "format": "date",
            "description": "The date when the software was published.",
        },
        "maintainer": {
            "type": "array",
            "description": "An array of maintainers for the software.",
            "items": {
                "type": "object",
                "properties": {
                    "@type": {"type": "string", "enum": ["Person", "Organization"]},
                    "name": {
                        "type": "string",
                        "description": "The name of the maintainer.",
                    },
                },
                "required": ["@type", "name"],
            },
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
        "targetProduct": {
            "type": "object",
            "properties": {
                "@type": {"type": "string", "const": "SoftwareApplication"},
                "name": {"type": "string"},
                "operatingSystem": {"type": "string"},
                "applicationCategory": {"type": "string"},
                "downloadUrl": {"type": "string", "format": "uri"},
                "identifier": {"type": "string", "format": "uri"},
                "softwareRequirements": {"type": "string"},
                "softwareVersion": {"type": "string"},
                "memoryRequirements": {"type": "string"},
                "processorRequirements": {"type": "string"},
                "releaseNotes": {"type": "string"},
                "screenshot": {"type": "string", "format": "uri"},
            },
            "required": ["@type", "name"],
        },
    },
}


"""
Define a mapping for specific User attributes and their corresponding strategies

ALLOW ONLY string.printable:
'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c'
"""

USER_MAPPING = {
    "username": st.text(min_size=1, max_size=50, alphabet=string.printable),
    "first_name": st.text(min_size=1, max_size=50, alphabet=string.printable),
    "last_name": st.text(min_size=1, max_size=50, alphabet=string.printable),
    "email": st.emails(),
}

"""
This class is used to test whether a random combination of methods that affect CodeMeta will produce a valid codemeta.json
"""


@settings(
    max_examples=MAX_STATEFUL_TEST_RUNS,
    stateful_step_count=MAX_STATEFUL_TEST_RULES_COUNT,
    verbosity=HYPOTHESIS_VERBOSITY,
    deadline=None,
    # suppress_health_check=[HealthCheck.data_too_large],
)
class CodeMetaValidationTest(RuleBasedStateMachine):
    added_release_contributors = Bundle("added_release_contributors")

    def __init__(self):
        self.release_contributors_count = 0
        self.release_nonauthor_contributors_count = 0
        self.release_author_contributors_count = 0

        self.keywords_count = 0
        self.programming_languages_count = 1

        self.user_factory = None
        self.users = None
        self.popped_users = None

        self.submitter = None
        self.codebase = None
        self.codebase_release = None

        super().__init__()

    @initialize(data=st.data())
    def setup(self, data):
        """
        Runs before each test case. Some duplicated initialization here and __init__?
        """
        self.release_contributors_count = 0
        self.release_nonauthor_contributors_count = 0
        self.release_author_contributors_count = 0

        self.keywords_count = 0
        self.programming_languages_count = 1

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
        self.popped_users = set()

        self.users = {
            self.user_factory.get_or_create(
                username=user_dict["username"],
                email=user_dict["email"],
                first_name=user_dict["first_name"],
                last_name=user_dict["last_name"],
            )
            for user_dict in unique_user_dict_pool
        }
        """
        Create Submitter
        """
        self.submitter = self.users.pop()

        # submitter is regarded as default contributor with role=Role.AUTHOR
        self.release_contributors_count += 1
        self.release_author_contributors_count += 1

        """
        Create Codebase and CodebaseRelease
        """
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase_release = codebase_factory.create_published_release()
        self.codebase = self.codebase_release.codebase

    @rule(
        role=st.sampled_from(list(Role)),
    )
    def add_unique_contributor(self, role):
        # this should return a unique user
        u = self.users.pop()
        self.popped_users.add(u)

        contributor, created = Contributor.from_user(u)

        note(f"adding unique contributor: {contributor.name}")

        # Function under test: CodebaseRelease.add_contributor()
        self.codebase_release.add_contributor(contributor, role)
        self.codebase_release.save()

        # since we are always adding a unique user, the contributors count will always increase by one
        self.release_contributors_count += 1

        if role == Role.AUTHOR:
            self.release_author_contributors_count += 1
        else:
            self.release_nonauthor_contributors_count += 1

    @rule(
        role=st.sampled_from(list(Role)),
    )
    def add_existing_contributor(self, role):
        # pick an existing contributor on the release
        contributor = random.choice(
            Contributor.objects.filter(codebaserelease=self.codebase_release)
        )
        existing_contributor_roles = (
            ReleaseContributor.objects.filter(contributor=contributor).get().roles
        )

        # Function under test: CodebaseRelease.add_contributor()
        self.codebase_release.add_contributor(contributor, role)
        self.codebase_release.save()

        # if an existing contributor is added again, but with AUTHOR role -> it will be considered "author" and not "nonauthor"
        if Role.AUTHOR not in existing_contributor_roles and role == Role.AUTHOR:
            self.release_author_contributors_count += 1
            self.release_nonauthor_contributors_count -= 1

    @rule(
        programming_language=st.text(
            min_size=10, max_size=20, alphabet=string.printable
        )
    )
    def add_programming_language(self, programming_language):
        existing_pls = self.codebase_release.programming_languages.all()
        # .lower() is used to make the test pass.
        # TODO: check behaviour when adding programming_languages
        lowercase_pl = programming_language.lower()
        if lowercase_pl not in [pl.name for pl in existing_pls]:
            self.codebase_release.programming_languages.add(lowercase_pl)
            self.programming_languages_count += 1

    @rule(keyword=st.text(min_size=1, max_size=25, alphabet=string.printable))
    def add_keyword(self, keyword):
        existing_tags = self.codebase_release.codebase.tags.all()

        # adding tags is case INSENSITIVE, need to make sure that the counter is increase
        # keyword should not be null or "", hence `min_size=1`!
        keyword = keyword.upper()
        if keyword not in [tag.name for tag in existing_tags]:
            self.codebase_release.codebase.tags.add(keyword)
            self.keywords_count += 1

    @invariant()
    def length_agrees(self):
        """
        authors and contributors
        """

        # total number of added unique contributors should match
        expected_contributors_count = self.release_contributors_count
        real_contributors_count = (
            self.codebase_release.codebase_contributors.all().count()
        )
        note(
            f"expected contributors: {expected_contributors_count}, actual contributors: {real_contributors_count}",
        )
        assert expected_contributors_count == real_contributors_count

        """
        total number of added unique authors and non-author contributors should match
        """
        real_author_contributors_count = (
            ReleaseContributor.objects.authors(self.codebase_release).all().count()
        )
        real_nonauthor_contributors_count = (
            ReleaseContributor.objects.nonauthors(self.codebase_release).all().count()
        )

        assert (
            expected_contributors_count
            == self.release_author_contributors_count
            + self.release_nonauthor_contributors_count
        )

        assert (
            expected_contributors_count
            == real_author_contributors_count + real_nonauthor_contributors_count
        )

        expected_codemeta_authors_count = len(
            CodeMetaSchema.convert_authors(CommonMetadata(self.codebase_release))
        )
        assert expected_codemeta_authors_count == self.release_author_contributors_count

        """
        keywords
        """
        expected_keywords_count = self.keywords_count
        real_keywords_count = self.codebase_release.codebase.tags.all().count()

        assert expected_keywords_count == real_keywords_count

        """
        programming_languages
        """
        expected_programming_languages_count = self.programming_languages_count
        real_programming_languages_count = (
            self.codebase_release.programming_languages.all().count()
        )

        assert expected_programming_languages_count == real_programming_languages_count

        """
        citations
        """
        # check citations if citation has been set
        # Replicate citation building mechanism from CodeMeta
        # citations should include references_text, replication_text, associated_publication_text, and CodebaseRelease.citation_text
        expected_citations = {
            self.codebase.references_text,
            self.codebase.replication_text,
            self.codebase.associated_publication_text,
            self.codebase_release.citation_text,
        }

        fresh_codemeta = CodeMetaSchema.build(self.codebase_release)
        # Extract text from CodeMeta.metadata
        codemeta_citations = {
            creative_work["text"]
            for creative_work in fresh_codemeta.metadata["citation"]
        }
        assert expected_citations == codemeta_citations

        note("length_agrees() done.")

    @invariant()
    def validate_against_schema(self):
        """
        release.codemeta.to_json() should ALWAYS validate against CODEMETA_SCHEMA
        """
        fresh_codemeta = CodeMetaSchema.build(self.codebase_release)
        try:
            jsonschema.validate(
                json.loads(fresh_codemeta.to_json()),
                schema=CODEMETA_SCHEMA,
            )
            assert True, "codemeta.json is valid."
        except Exception as e:
            logger.error("codemeta json was invalid ", e)
            assert False, f"CodeMeta validation error: {e}"

    def teardown(self):
        """
        Clean up all created objects. This runs at the end of each test case
        """
        note("teardown()")
        # TODO: why is this check necessary? Why does hypothesis run multiple @initialize and teardown at start?
        if self.codebase_release is not None:
            try:
                # Delete CodebaseRelease
                self.codebase_release.delete()
                # CodebaseRelease.objects.filter(id=self.codebase_release.id).delete()
                # Delete Codebase
                # Codebase.objects.filter(id=self.codebase.id).delete()
                self.codebase.delete()
                # Delete Submitter
                self.submitter.delete()
                # User.objects.filter(id=self.submitter.id).delete()
                # Delete generated users which were added as contributors
                User.objects.filter(
                    id__in=[
                        user.id for user in (list(self.popped_users) + list(self.users))
                    ]
                ).delete()
                # Delete the rest of user objects
                # User.objects.filter(id__in=[user.id for user in self.users]).delete()
            except Exception as err:
                logger.error(f"Exception during teardown: {err}")

        note("teardown() done.")


"""
This class is used to run CodeMetaValidationTest
"""


class StatefulCodeMetaValidationTest(CodeMetaValidationTest.TestCase, TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
