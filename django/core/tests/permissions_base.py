from django.test import TestCase
from django.urls import resolve
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from core.queryset import get_viewable_objects_for_user
from django.contrib.auth.models import AnonymousUser, User


class UrlChecker:
    def __init__(self, view_name, test_case_cls):
        self.view_name = view_name
        self.test_case_cls = test_case_cls

    def assertInstanceUrlResolutionIsIdempotent(self, instance):
        # instance with kwargs not valid for the url will result in a
        # NoReverseMatch exception
        path = instance.get_absolute_url()
        resolved = resolve(path)
        self.test_case_cls.assertEqual(self.view_name, resolved.view_name)


class SerializerChecker:
    def __init__(self, serializer, test_case_cls):
        self.serializer = serializer
        self.test_case_cls = test_case_cls

    def assertSerializationIsIdempotent(self, instance):
        serialized = self.serializer(instance)
        deserialized = self.serializer(instance, data=serialized.data)
        if deserialized.is_valid(raise_exception=True):
            updated_instance = deserialized.save()
            self.test_case_cls.assertEqual(instance, updated_instance)


def create_perm_str(instance, perm_name):
    return "{}.{}_{}".format(instance._meta.app_label, perm_name, instance._meta.model_name)


class ViewMethod:
    def __init__(self, name, model):
        self.name = name
        self.perm_str = create_perm_str(model, name)


class HasPermission(Exception): pass


class DoesNotHavePermission(Exception): pass


class LoginFailure(Exception): pass


class ApiAccountMixin:
    def create_representative_users(self, submitter, user_factory=None):
        # Inactive users cannot login so are not included
        if not user_factory:
            user_factory = self.user_factory
        self.regular_user = user_factory.create(username='regular')
        self.superuser = user_factory.create(username='superuser', is_superuser=True)
        self.anonymous_user = AnonymousUser()
        self.submitter = submitter

    @property
    def users_able_to_login(self):
        return [self.regular_user, self.superuser, self.submitter]

    def login(self, user, password):
        if not user.is_active:
            return user, False
        logged_in = self.client.login(username=user.username, password=password)
        if not logged_in:
            if user.is_active:
                raise LoginFailure()
        return user, logged_in


class ResponseStatusCodesMixin:
    def responseErrorMessage(self, response, name):
        user = response.wsgi_request.user
        user_msg = '<{} is_superuser={} is_active={} is_anonymous={}>'.format(
            user.username, user.is_superuser, user.is_active, user.is_anonymous)
        data = getattr(response, 'data', None)
        msg = 'Response not {} for user {}'.format(name, user_msg)
        if data is not None:
            msg += '. Got {}'.format(data)
        return msg

    def assertResponseOk(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=self.responseErrorMessage(response, 'OK'))

    def assertResponseCreated(self, response):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         msg=self.responseErrorMessage(response, 'CREATED'))

    def assertResponseAccepted(self, response):
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED,
                         msg=self.responseErrorMessage(response, 'ACCEPTED'))

    def assertResponseFound(self, response):
        self.assertEqual(response.status_code, status.HTTP_302_FOUND,
                         msg=self.responseErrorMessage(response, 'FOUND'))

    def assertResponseDeleted(self, response):
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT,
                         msg=self.responseErrorMessage(response, 'NO_CONTENT'))

    def assertResponsePermissionDenied(self, response):
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg=self.responseErrorMessage(response, 'FORBIDDEN'))

    def assertResponseNotFound(self, response):
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         msg=self.responseErrorMessage(response, 'NOT FOUND'))

    def assertResponseMethodNotAllowed(self, response):
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         msg=self.responseErrorMessage(response, 'METHOD NOT ALLOWED'))


class BaseViewSetTestCase(ApiAccountMixin, ResponseStatusCodesMixin, APITestCase):
    _view = None

    @property
    def view_class(self):
        return self._view

    @property
    def serializer_class(self):
        return self.view_class().get_serializer_class()

    @property
    def model_class(self):
        return self.serializer_class().Meta.model

    def check_retrieve_permissions(self, user, instance):
        """Validate view permissions against a user with no initial guardian permissions.
        Does not handle being inside a collection of another model"""
        response = self.client.get(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(self.model_class(), 'view'), obj=instance)
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_create_permissions(self, user, create_data):
        response = self.client.post(self.model_class().get_list_url(), create_data, HTTP_ACCEPT='application/json',
                                    format='json')
        has_perm = user.has_perm(create_perm_str(self.model_class(), 'add'))
        if has_perm:
            self.assertResponseCreated(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_update_permissions(self, user, instance):
        serialized = self.serializer_class(instance)
        response = self.client.put(instance.get_absolute_url(), serialized.data, HTTP_ACCEPT='application/json',
                                   format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'change'), obj=instance)
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_destroy_permissions(self, user, instance):
        response = self.client.delete(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'delete'), obj=instance)
        if has_perm:
            self.assertResponseDeleted(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_list_permissions(self, user, instance):
        """A user has list view permissions on an instance if the instance is public"""
        list_response = self.client.get(instance.get_list_url(), HTTP_ACCEPT='application/json', format='json')
        self.assertResponseOk(list_response)
        is_visible_in_list = len(list_response.data['results']) > 0
        is_instance_public = instance._meta.model.objects.public().filter(pk=instance.pk).exists()
        self.assertEqual(is_visible_in_list, is_instance_public)

    def with_logged_in(self, user, instance, method):
        self.login(user, password=self.user_factory.password)
        method(user, instance)
        self.client.logout()

    def check_retrieve(self):
        for user in self.users_able_to_login:
            self.with_logged_in(user, self.instance, self.check_retrieve_permissions)
            assign_perm(create_perm_str(self.instance, 'view'), user_or_group=user, obj=self.instance)
            self.with_logged_in(user, self.instance, self.check_retrieve_permissions)
        self.check_retrieve_permissions(self.anonymous_user, self.instance)

    def check_destroy(self):
        for user in self.users_able_to_login:
            instance = self.instance_factory.create()
            self.with_logged_in(user, instance, self.check_destroy_permissions)
            other_instance = self.instance_factory.create()
            assign_perm(create_perm_str(other_instance, 'delete'), user_or_group=user, obj=other_instance)
            self.with_logged_in(user, other_instance, self.check_destroy_permissions)
        instance = self.instance_factory.create()
        self.check_destroy_permissions(self.anonymous_user, instance)

    def check_update(self):
        for user in self.users_able_to_login:
            instance = self.instance_factory.create()
            self.with_logged_in(user, instance, self.check_update_permissions)
            assign_perm(create_perm_str(self.instance, 'change'), user_or_group=user, obj=instance)
            self.with_logged_in(user, instance, self.check_update_permissions)
        instance = self.instance_factory.create()
        self.check_update_permissions(self.anonymous_user, instance)

    def check_create(self):
        for user in self.users_able_to_login:
            create_data = self.instance_factory.data_for_create_request()
            self.with_logged_in(user, create_data, self.check_create_permissions)
        create_data = self.instance_factory.data_for_create_request()
        self.check_create_permissions(self.anonymous_user, create_data)

    def check_list(self):
        for user in self.users_able_to_login:
            self.with_logged_in(user, self.instance, self.check_list_permissions)
            assign_perm(create_perm_str(self.instance, 'view'), user_or_group=user, obj=self.instance)
            self.with_logged_in(user, self.instance, self.check_list_permissions)
        self.check_list_permissions(self.anonymous_user, self.instance)
