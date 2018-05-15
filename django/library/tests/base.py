import random
from uuid import UUID

from django.contrib.auth.models import User
from django.test import TestCase

from library.models import Codebase, CodebaseRelease, ReleaseContributor, Contributor, PeerReviewerFeedback, \
    PeerReviewInvitation, PeerReview
from library.serializers import CodebaseSerializer


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = self.create_user()

    def create_user(self, username='test_user', password='test', **kwargs):
        kwargs.setdefault('email', 'testuser@mailinator.com')
        return User.objects.create_user(username=username, password=password, **kwargs)


class CodebaseFactory:
    def __init__(self, submitter):
        self.id = 0
        self.submitter = submitter

    def get_default_data(self):
        uuid = UUID(int=random.getrandbits(128))
        return {
            'title': 'Wolf Sheep Predation',
            'description': 'Wolf sheep predation model in NetLogo with grass',
            'uuid': uuid,
            'identifier': str(uuid),
            'submitter': self.submitter
        }

    def create(self, **overrides) -> Codebase:
        codebase = self.create_unsaved(**overrides)
        codebase.save()
        return codebase

    def create_unsaved(self, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return Codebase(**kwargs)

    def data_for_create_request(self, **overrides):
        codebase = self.create_unsaved(**overrides)
        codebase.id = 0
        serialized = CodebaseSerializer(codebase).data
        del serialized['id']
        return serialized


class ContributorFactory:
    def __init__(self, user):
        self.user = user

    def get_default_data(self, user):
        if user is None:
            user = self.user
        return {
            'given_name': user.first_name,
            'family_name': user.last_name,
            'type': 'person',
            'email': user.email,
            'user': user
        }

    def create(self, **overrides) -> Contributor:
        kwargs = self.get_default_data(overrides.get('user'))
        kwargs.update(overrides)
        return Contributor.objects.create(**kwargs)


class ReleaseContributorFactory:
    def __init__(self, codebase_release):
        self.codebase_release = codebase_release
        self.index = 0

    def get_default_data(self):
        defaults = {
            'release': self.codebase_release,
            'index': self.index
        }
        self.index += 1
        return defaults

    def create(self, contributor: Contributor, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return ReleaseContributor.objects.create(contributor=contributor, **kwargs)


class CodebaseReleaseFactory:
    def __init__(self, codebase, submitter = None):
        if submitter is None:
            submitter = codebase.submitter
        self.submitter = submitter
        self.codebase = codebase

    def get_default_data(self):
        return {
            'description': 'Added rational utility decision making to wolves',
            'submitter': self.submitter,
            'codebase': self.codebase,
            'live': True
        }

    def create(self, **defaults) -> CodebaseRelease:
        kwargs = self.get_default_data()
        kwargs.update(defaults)

        codebase = kwargs.pop('codebase')
        submitter = kwargs.pop('submitter')

        codebase_release = codebase.import_release(submitter=submitter)
        for k, v in kwargs.items():
            if hasattr(codebase_release, k):
                setattr(codebase_release, k, v)
            else:
                raise KeyError('Key "{}" is not a property of codebase'.format(k))
        codebase_release.save()
        return codebase_release


class PeerReviewFactory:
    def __init__(self, submitter, codebase_release):
        self.submitter = submitter
        self.codebase_release = codebase_release

    def get_default_data(self):
        return {
            'submitter': self.submitter,
            'codebase_release': self.codebase_release
        }

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
            'candidate_reviewer': self.reviewer,
            'editor': self.editor,
            'review': self.review
        }

    def create(self, **defaults):
        kwargs = self.get_default_data()
        kwargs.update(defaults)

        invitation = PeerReviewInvitation(**kwargs)
        invitation.save()
        return invitation

