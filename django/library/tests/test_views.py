import pathlib

import io
import shutil
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase, create_perm_str, ResponseStatusCodesMixin, ApiAccountMixin
from library.fs import FileCategoryDirectories
from library.models import Codebase
from .base import CodebaseFactory, ContributorFactory, ReleaseContributorFactory
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
        self.instance.create_release(live=True, draft=False, initialize=False)

    def assertResponseNoPermission(self, instance, response):
        if instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_retrieve_permissions(self, user, instance):
        response = self.client.get(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(self.model_class(), 'view'), obj=instance)
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertResponseNoPermission(instance, response)

    def check_destroy_permissions(self, user, instance):
        has_perm = user.has_perm(create_perm_str(instance, 'delete'), obj=instance)
        if has_perm:
            # delete all dependent codebases first
            for codebase in user.codebases.all():
                codebase.releases.all().delete()
                codebase.delete()

        response = self.client.delete(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        if user.is_anonymous:
            self.assertResponsePermissionDenied(response)
            return
        if has_perm:
            self.assertResponseDeleted(response)
        elif instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_update_permissions(self, user, instance):
        serialized = self.serializer_class(instance)
        response = self.client.put(instance.get_absolute_url(), serialized.data, HTTP_ACCEPT='application/json',
                                   format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'change'), obj=instance)
        if user.is_anonymous:
            self.assertResponsePermissionDenied(response)
            return
        if has_perm:
            self.assertResponseOk(response)
        elif instance.live:
            self.assertResponsePermissionDenied(response)
        else:
            self.assertResponseNotFound(response)

    def check_destroy(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            self.instance.create_release(initialize=False)
            codebase = Codebase.objects.get(pk=codebase.id)
            self.with_logged_in(user, codebase, self.check_destroy_permissions)

            other_codebase = self.instance_factory.create()
            other_codebase.create_release(initialize=False)
            other_codebase = Codebase.objects.get(pk=other_codebase.id)
            assign_perm(create_perm_str(other_codebase, 'delete'), user_or_group=user, obj=other_codebase)
            self.with_logged_in(user, other_codebase, self.check_destroy_permissions)

        codebase = self.instance_factory.create()
        codebase.create_release(initialize=False)
        codebase = Codebase.objects.get(pk=codebase.id)
        self.check_destroy_permissions(self.anonymous_user, codebase)

    def check_update(self):
        for user in self.users_able_to_login:
            codebase = self.instance_factory.create()
            codebase.create_release(initialize=False)
            codebase = Codebase.objects.get(pk=codebase.id)
            self.with_logged_in(user, codebase, self.check_update_permissions)
            assign_perm(create_perm_str(self.instance, 'change'), user_or_group=user, obj=codebase)
            self.with_logged_in(user, codebase, self.check_update_permissions)

        codebase = self.instance_factory.create()
        codebase.create_release(initialize=False)
        codebase = Codebase.objects.get(pk=codebase.id)
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
        self.codebase_release = self.codebase.create_release(draft=False, initialize=False)
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


class CodebaseReleaseUnpublishedFilesTestCase(ApiAccountMixin, ResponseStatusCodesMixin, TestCase):
    """Test file handling for creating a release. Only user with change permission on a unpublished release should be
    able to list, destroy or create files. No user should be able to create or destroy files from a published release"""

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username='submitter')
        self.superuser = self.user_factory.create(username='superuser', is_superuser=True)
        self.other_user = self.user_factory.create(username='other_user')
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(draft=False, initialize=False)

    def test_upload_file(self):
        api = self.codebase_release.get_fs_api()

        # Unpublished codebase release permissions
        response = self.client.post(api.get_originals_list_url(category=FileCategoryDirectories.code))
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_400_BAD_REQUEST),
                                           (self.superuser, status.HTTP_400_BAD_REQUEST),
                                           (self.other_user, status.HTTP_404_NOT_FOUND)]:
            self.login(user, self.user_factory.password)
            response = self.client.post(api.get_originals_list_url(category=FileCategoryDirectories.code),
                                        HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg='{} {}'.format(repr(user), response.data))

        self.codebase_release.live = True
        self.codebase_release.draft = False
        self.codebase_release.save()

        # Published codebase release permissions
        self.client.logout()
        response = self.client.post(
            api.get_originals_list_url(category=FileCategoryDirectories.code))
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_403_FORBIDDEN),
                                           (self.superuser, status.HTTP_403_FORBIDDEN),
                                           (self.other_user, status.HTTP_403_FORBIDDEN)]:
            self.login(user, self.user_factory.password)
            response = self.client.post(
                api.get_originals_list_url(category=FileCategoryDirectories.code),
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg='{} {}'.format(repr(user), response.data))

    def test_list_files(self):
        api = self.codebase_release.get_fs_api()

        # Unpublished codebase release permissions
        response = self.client.get(
            api.get_originals_list_url(category=FileCategoryDirectories.code))
        self.assertResponseNotFound(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_200_OK),
                                           (self.superuser, status.HTTP_200_OK),
                                           (self.other_user, status.HTTP_404_NOT_FOUND)]:
            self.login(user, self.user_factory.password)
            response = self.client.get(api.get_originals_list_url(FileCategoryDirectories.code),
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg='{} {}'.format(repr(user), response.data))

        self.codebase_release.live = True
        self.codebase_release.draft = False
        self.codebase_release.save()
        self.client.logout()

        # Published codebase release permissions
        response = self.client.get(api.get_originals_list_url(FileCategoryDirectories.code))
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_403_FORBIDDEN),
                                           (self.superuser, status.HTTP_403_FORBIDDEN),
                                           (self.other_user, status.HTTP_403_FORBIDDEN)]:
            self.login(user, self.user_factory.password)
            response = self.client.get(api.get_originals_list_url(FileCategoryDirectories.code),
                                       HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg='{} {}'.format(repr(user), response.data))

    def test_delete_file(self):
        path_to_foo = pathlib.Path('foo.txt')
        api = self.codebase_release.get_fs_api()

        # Unpublished codebase release permissions
        response = self.client.delete(
            api.get_absolute_url(category=FileCategoryDirectories.code,
                                 relpath=path_to_foo))
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_400_BAD_REQUEST),
                                           (self.superuser, status.HTTP_400_BAD_REQUEST),
                                           (self.other_user, status.HTTP_404_NOT_FOUND)]:
            self.login(user, self.user_factory.password)
            response = self.client.delete(
                api.get_absolute_url(category=FileCategoryDirectories.code,
                                     relpath=path_to_foo),
                HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg=repr(user))

        self.codebase_release.live = True
        self.codebase_release.draft = False
        self.codebase_release.save()
        self.client.logout()

        # Published codebase release permissions
        response = self.client.delete(
            api.get_absolute_url(category=FileCategoryDirectories.code,
                                 relpath=path_to_foo))
        self.assertResponsePermissionDenied(response)
        for user, expected_status_code in [(self.submitter, status.HTTP_403_FORBIDDEN),
                                           (self.superuser, status.HTTP_403_FORBIDDEN),
                                           (self.other_user, status.HTTP_403_FORBIDDEN)]:
            self.login(user, self.user_factory.password)
            response = self.client.delete(api.get_absolute_url(FileCategoryDirectories.code, path_to_foo),
                                          HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, expected_status_code, msg=repr(user))


class CodebaseReleaseDraftViewTestCase(ApiAccountMixin, ResponseStatusCodesMixin, TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username='submitter')
        self.other_user = self.user_factory.create(username='other_user')
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        self.codebase_release = self.codebase.create_release(draft=False, live=False, initialize=False)
        self.path = self.codebase.get_draft_url()

    def test_release_creation_only_if_codebase_change_permission(self):
        response = self.client.post(path=self.path)
        self.assertResponsePermissionDenied(response)

        self.login(self.other_user, self.user_factory.password)
        response_other_user = self.client.post(path=self.path)
        self.assertResponsePermissionDenied(response_other_user)

        self.login(self.submitter, self.user_factory.password)
        response_submitter = self.client.post(path=self.path)
        self.assertResponseFound(response_submitter)


class ViewUrlRegexTestCase(TestCase):
    def test_download_unpublished(self):
        reverse('library:codebaserelease-original-files-detail',
                kwargs={'version_number': '1.0.0', 'identifier': 'a822d39c-3e62-45a4-bf87-3340f524910c',
                        'relpath': 'converted/206/3-4/round3.17.save-bot-data.csv', 'category': 'code'})


class CodebaseReleasePublishTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create()
        codebase_factory = CodebaseFactory(submitter=self.submitter)
        self.codebase = codebase_factory.create()
        # Want to test get_fs_api creates the file system even if file system is not initialized properly
        self.codebase_release = self.codebase.create_release(initialize=False)
        contributor_factory = ContributorFactory(user=self.submitter)
        self.contributor = contributor_factory.create()
        self.release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)

    def test_publish_codebaserelease(self):
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        self.release_contributor_factory.create(self.contributor)
        with self.assertRaises(ValidationError):
            self.codebase_release.publish()

        self.client.login(username=self.submitter.username, password=self.user_factory.password)
        response = self.client.post(self.codebase_release.regenerate_share_url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

        code_file = io.BytesIO(bytes('Hello world!', 'utf8'))
        code_file.name = 'test.nlogo'

        docs_file = io.BytesIO(bytes('A new model', 'utf8'))
        docs_file.name = 'README.md'

        api = self.codebase_release.get_fs_api()
        api.add(content=code_file, category=FileCategoryDirectories.code)
        api.add(content=docs_file, category=FileCategoryDirectories.docs)
        self.codebase_release.publish()

        download_response = self.client.get(self.codebase_release.review_download_url)
        self.assertEqual(download_response.status_code, 404)
        response = self.client.post(self.codebase_release.regenerate_share_url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)


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
        self.codebase_release = self.codebase.create_release(initialize=False)
        release_contributor_factory = ReleaseContributorFactory(codebase_release=self.codebase_release)
        release_contributor_factory.create(contributor=contributor)

    def test_detail(self):
        response = self.client.get(reverse('library:codebaserelease-detail',
                                           kwargs={'identifier': self.codebase.identifier,
                                                   'version_number': self.codebase_release.version_number}))
        self.assertTrue(response.status_code, True)


def tearDownModule():
    shutil.rmtree(settings.LIBRARY_ROOT, ignore_errors=True)
