import io

import shutil

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase, create_perm_str
from library.models import Codebase
from .base import CodebaseFactory, CodebaseReleaseFactory, ContributorFactory, ReleaseContributorFactory
from ..views import CodebaseViewSet, CodebaseReleaseViewSet


class CodebaseViewSetTestCase(BaseViewSetTestCase):
    _view = CodebaseViewSet

    @property
    def serializer_class(self):
        view = self.view_class()
        view.action = self.action
        return view.get_serializer_class()

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create()
        self.create_representative_users(submitter)
        self.instance_factory = CodebaseFactory(submitter=submitter)
        self.instance = self.instance_factory.create()
        self.release_factory = CodebaseReleaseFactory(submitter=submitter, codebase=self.instance)
        self.release_factory.create(live=True)

    def assertResponseNoPermission(self, instance, response):
        if instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_destroy(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            self.release_factory.create(codebase=codebase)
            codebase = Codebase.objects.with_liveness().get(id=codebase.id)
            self.with_logged_in(user, codebase, self.check_destroy_permissions)

            other_codebase = self.instance_factory.create()
            self.release_factory.create(codebase=other_codebase)
            other_codebase = Codebase.objects.with_liveness().get(id=other_codebase.id)
            assign_perm(create_perm_str(other_codebase, 'delete'), user_or_group=user, obj=other_codebase)
            self.with_logged_in(user, other_codebase, self.check_destroy_permissions)

        codebase = self.instance_factory.create()
        self.release_factory.create(codebase=codebase)
        codebase = Codebase.objects.with_liveness().get(id=codebase.id)
        self.check_destroy_permissions(self.anonymous_user, codebase)

    def check_update(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            self.release_factory.create(codebase=codebase)
            codebase = Codebase.objects.with_liveness().get(id=codebase.id)
            self.with_logged_in(user, codebase, self.check_update_permissions)
            assign_perm(create_perm_str(self.instance, 'change'), user_or_group=user, obj=codebase)
            self.with_logged_in(user, codebase, self.check_update_permissions)

        codebase = self.instance_factory.create()
        self.release_factory.create(codebase=codebase)
        codebase = Codebase.objects.with_liveness().get(id=codebase.id)
        self.check_update_permissions(self.anonymous_user, codebase)

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
        self.submitter = self.user_factory.create(username='submitter')
        self.other_user = self.user_factory.create(username='other_user')
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(draft=False)
        self.path = self.codebase_release.get_list_url()

    def test_release_creation_only_if_codebase_change_permission(self):
        response = self.client.post(path=self.path, format='json')
        self.assertResponsePermissionDenied(response)

        self.login(self.other_user, self.user_factory.password)
        response_other_user = self.client.post(path=self.path, data=None, HTTP_ACCEPT='application/json', format='json')
        self.assertResponsePermissionDenied(response_other_user)

        self.login(self.submitter, self.user_factory.password)
        response_submitter = self.client.post(path=self.path, HTTP_ACCEPT='application/json', format='json')
        self.assertResponseCreated(response_submitter)


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
        self.codebase_release = codebase_release_factory.create(live=False)
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
