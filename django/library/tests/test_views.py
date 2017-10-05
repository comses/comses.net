from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase
from .base import CodebaseFactory, CodebaseReleaseFactory, ContributorFactory, ReleaseContributorFactory
from ..views import CodebaseViewSet, CodebaseReleaseViewSet


class CodebaseViewSetTestCase(BaseViewSetTestCase):
    _view = CodebaseViewSet
    _retrieve_error_code = status.HTTP_404_NOT_FOUND

    @property
    def serializer_class(self):
        view = self.view_class()
        view.action = self.action
        return view.get_serializer_class()

    def setUp(self):
        self.user_factory = UserFactory()
        self.user_factory = UserFactory()
        submitter = self.user_factory.create()
        self.representative_users = [AnonymousUser()]
            # self.create_representative_users(submitter)
        self.instance_factory = CodebaseFactory(submitter=submitter)
        self.instance = self.instance_factory.create()

    def test_retrieve(self):
        self.action = 'retrieve'
        self.check_retrieve()

    def test_update(self):
        self.action = 'update'
        self.check_update()

    def test_destroy(self):
        self.action = 'destroy'
        self.check_destroy()

    def test_create(self):
        self.action = 'create'
        self.check_create()

    def test_list(self):
        self.action = 'list'
        self.check_list()


class CodebaseReleaseViewSetTestCase(BaseViewSetTestCase):
    _view = CodebaseReleaseViewSet

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create()
        self.representative_users = self.create_representative_users(submitter)


class CodebaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()

    def test_list(self):
        response = self.client.get(reverse('library:codebase-detail', kwargs={'identifier': self.codebase.identifier}))
        self.assertTrue(response.status_code, 200)


class CodebaseReleaseRenderPageTestCase(TestCase):
    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        contributor_factory = ContributorFactory()
        codebase_release_factory = CodebaseReleaseFactory()

        contributor = contributor_factory.create(user=self.submitter)

        self.codebase = codebase_factory.create(submitter=self.submitter)
        self.codebase_release = codebase_release_factory.create(codebase=self.codebase)
        release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)
        release_contributor_factory.create(contributor=contributor)

    def test_detail(self):
        response = self.client.get(reverse('library:codebaserelease-detail',
                                           kwargs={'identifier': self.codebase.identifier,
                                                   'version_number': self.codebase_release.version_number}))
        self.assertTrue(response.status_code, True)
