from django.contrib.auth.models import User
from django.test import TestCase
from ..models import Codebase, CodebaseRelease, ReleaseContributor, Contributor
from uuid import UUID
import random


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = self.create_user()

    def create_user(self, username='test_user', password='test', email='testuser@mailinator.com', **kwargs):
        return User.objects.create_user(username=username, password=password, **kwargs)


class CodebaseFactory:
    def __init__(self):
        self.id = 0

    def get_default_data(self):
        uuid = UUID(int=random.getrandbits(128))
        return {
            'title': 'Wolf Sheep Predation',
            'description': 'Wolf sheep predation model in NetLogo with grass',
            'uuid': uuid,
            'identifier': str(uuid)
        }

    def create(self, submitter, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return Codebase.objects.create(submitter=submitter, **kwargs)


class ContributorFactory:
    def get_default_data(self, user):
        return {
            'given_name': user.first_name,
            'family_name': user.last_name,
            'type': 'person',
            'email': user.email,
            'user': user
        }

    def create(self, user, **overrides):
        kwargs = self.get_default_data(user)
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
    def get_default_data(self):
        return {
            'description': 'Added rational utility decision making to wolves',
        }

    def create(self, codebase: Codebase, submitter=None, **defaults):
        if submitter is None:
            submitter = codebase.submitter
        codebase_release = codebase.make_release(submitter=submitter)
        kwargs = self.get_default_data()
        kwargs.update(defaults)
        for k, v in kwargs.items():
            if hasattr(codebase_release, k):
                setattr(codebase_release, k, v)
            else:
                raise KeyError('Key "{}" is not a property of codebase'.format(k))
        codebase_release.save()
        return codebase_release
