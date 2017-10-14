import io

import shutil

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase, create_perm_str
from library.models import CodebaseReleasePublisher
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
        self.representative_users = self.create_representative_users(submitter)
        self.instance_factory = CodebaseFactory(submitter=submitter)
        self.instance = self.instance_factory.create()
        self.instance.live = False

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


class CodebaseReleasePublishTestCase(TestCase):
    # Without this empty setupClass I get a django "InterfaceError: connection already closed" error
    # May be related to https://groups.google.com/forum/#!msg/django-users/MDRcg4Fur98/hCRe5nGvAwAJ
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        codebase_release_factory = CodebaseReleaseFactory(submitter=self.submitter, codebase=self.codebase)
        self.codebase_release = codebase_release_factory.create()
        contributor_factory = ContributorFactory(user=self.submitter)
        self.contributor = contributor_factory.create()
        self.release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)

    def test_publish_codebaserelease(self):
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        self.release_contributor_factory.create(self.contributor)
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        fileobj = io.BytesIO(bytes('Hello world!', 'utf8'))
        fileobj.name = 'test.nlogo'
        self.codebase_release.add_upload(upload_type='sources', fileobj=fileobj)
        self.codebase_release.publish()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.LIBRARY_ROOT, ignore_errors=True)


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
        contributor_factory = ContributorFactory(user=self.submitter)
        contributor = contributor_factory.create(user=self.submitter)

        self.codebase = codebase_factory.create(submitter=self.submitter)
        codebase_release_factory = CodebaseReleaseFactory(submitter=self.submitter, codebase=self.codebase)
        self.codebase_release = codebase_release_factory.create()
        release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)
        release_contributor_factory.create(contributor=contributor)

    def test_detail(self):
        response = self.client.get(reverse('library:codebaserelease-detail',
                                           kwargs={'identifier': self.codebase.identifier,
                                                   'version_number': self.codebase_release.version_number}))
        self.assertTrue(response.status_code, True)
