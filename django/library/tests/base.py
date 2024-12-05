import io
import logging
import random
from uuid import UUID

from core.tests.base import ContentModelFactory, UserFactory
from library.fs import FileCategoryDirectories
from library.models import (
    Codebase,
    CodebaseRelease,
    License,
    Role,
    Contributor,
    PeerReviewInvitation,
    PeerReview,
    PeerReviewer,
)
from library.serializers import CodebaseSerializer


logger = logging.getLogger(__name__)


class CodebaseFactory(ContentModelFactory):
    model = Codebase
    serializer = CodebaseSerializer

    def __init__(self, submitter):
        super().__init__(submitter)
        self.id = 0

    def get_default_data(self):
        uuid = UUID(int=random.getrandbits(128))
        return {
            "title": "Wolf Sheep Predation",
            "description": "Wolf sheep predation model in NetLogo with grass",
            "uuid": uuid,
            "identifier": str(uuid),
            "submitter": self.submitter,
            "references_text": "Wilensky, U. (1997). NetLogo Wolf Sheep Predation model.",
            "replication_text": "This model is a replication of the NetLogo model.",
            "associated_publication_text": "This model is associated with a publication.",
        }

    def data_for_create_request(self, **overrides):
        codebase = self.create_unsaved(**overrides)
        codebase.id = 0
        serialized = CodebaseSerializer(codebase).data
        del serialized["id"]
        return serialized

    def create_published_release(self, codebase=None, **kwargs):
        if codebase is None:
            codebase, created = self.get_or_create(
                **kwargs, defaults=self.get_default_data()
            )
        release = ReleaseSetup.setUpPublishableDraftRelease(codebase)
        release.publish(defer_fs=True)
        return release


class ContributorFactory:
    def __init__(self, user):
        self.user = user

    def get_default_data(self, user):
        if user is None:
            user = self.user
        return {
            "given_name": user.first_name,
            "family_name": user.last_name,
            "type": "person",
            "email": user.email,
            "user": user,
        }

    def create(self, **overrides) -> Contributor:
        default_data = self.get_default_data(overrides.get("user"))
        default_data.update(overrides)
        user = default_data.pop("user")
        contributor, created = Contributor.objects.get_or_create(
            user=user, defaults=default_data
        )
        return contributor


class ReleaseContributorFactory:
    def __init__(self, codebase_release):
        self.codebase_release = codebase_release
        self.index = 0

    def get_default_data(self):
        defaults = {"role": Role.AUTHOR, "index": self.index}
        self.index += 1
        return defaults

    def create(self, contributor: Contributor, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return self.codebase_release.add_contributor(contributor, **kwargs)


class PeerReviewFactory:
    def __init__(self, submitter, codebase_release):
        self.submitter = submitter
        self.codebase_release = codebase_release

    def get_default_data(self):
        return {"submitter": self.submitter, "codebase_release": self.codebase_release}

    def create(self, **defaults):
        kwargs = self.get_default_data()
        kwargs.update(defaults)

        review = PeerReview(**kwargs)
        review.save()
        return review


class PeerReviewInvitationFactory:
    def __init__(self, editor, reviewer, review):
        self.editor = editor
        self.review = review
        self.reviewer = reviewer

    def get_default_data(self):
        return {
            "candidate_reviewer": self.reviewer.member_profile,
            "reviewer": self.reviewer,
            "editor": self.editor,
            "review": self.review,
        }

    def create(self, **defaults):
        kwargs = self.get_default_data()
        kwargs.update(defaults)

        invitation = PeerReviewInvitation(**kwargs)
        invitation.save()
        return invitation


class ReviewSetup:
    @classmethod
    def setUpReviewData(cls):
        cls.user_factory = UserFactory()
        cls.editor = cls.user_factory.create().member_profile
        reviewer = cls.user_factory.create().member_profile
        cls.reviewer = PeerReviewer.objects.create(member_profile=reviewer)
        cls.submitter = cls.user_factory.create()

        cls.codebase_factory = CodebaseFactory(cls.submitter)
        cls.codebase = cls.codebase_factory.create()
        cls.codebase_release = cls.codebase.create_release(initialize=False)
        cls.review_factory = PeerReviewFactory(
            submitter=cls.codebase.submitter.member_profile,
            codebase_release=cls.codebase_release,
        )
        cls.review = cls.review_factory.create()


class ReleaseSetup:
    @classmethod
    def setUpPublishableDraftRelease(cls, codebase):
        draft_release = codebase.create_release(
            status=CodebaseRelease.Status.DRAFT,
            initialize=True,
        )
        draft_release.license, created = License.objects.get_or_create(name="MIT")
        draft_release.os = "Any"
        draft_release.programming_languages.add("Python")
        contributor_factory = ContributorFactory(user=draft_release.submitter)
        release_contributor_factory = ReleaseContributorFactory(draft_release)
        contributor = contributor_factory.create()
        release_contributor_factory.create(contributor)

        code_file = io.BytesIO(b"print('hello world')")
        code_file.name = "some_code_file.py"
        docs_file = io.BytesIO(b"# Documentation")
        docs_file.name = "some_doc_file.md"
        fs_api = draft_release.get_fs_api()
        fs_api.add(content=code_file, category=FileCategoryDirectories.code)
        fs_api.add(content=docs_file, category=FileCategoryDirectories.docs)

        draft_release.save()

        return draft_release
