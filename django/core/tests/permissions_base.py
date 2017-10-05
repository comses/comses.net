from django.test import TestCase
from django.urls import resolve
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from core.backends import get_viewable_objects_for_user
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


class BaseViewSetTestCase(APITestCase):
    _view = None
    _retrieve_error_code = status.HTTP_403_FORBIDDEN

    @property
    def view_class(self):
        return self._view

    @property
    def serializer_class(self):
        return self.view_class().get_serializer_class()

    @property
    def model_class(self):
        return self.serializer_class().Meta.model

    def create_representative_users(self, submitter):
        return [
            self.user_factory.create(is_active=False),
            self.user_factory.create(),
            self.user_factory.create(is_active=False, is_superuser=True),
            self.user_factory.create(is_superuser=True),
            AnonymousUser(),
            submitter,
        ]

    def assertResponseCreated(self, response):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def assertResponseOk(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def assertResponseDeleted(self, response):
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def assertResponseAccepted(self, response):
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def assertResponsePermissionDenied(self, request):
        self.assertEqual(request.status_code, status.HTTP_403_FORBIDDEN)

    def login(self, user, password):
        success = self.client.login(username=user.username, password=password)
        if success:
            return user
        else:
            return AnonymousUser()

    def check_retrieve_permissions(self, user, instance, password):
        """validate view permissions against a user with no initial guardian permissions"""
        user = self.login(user, password)
        self.client.credentials()
        response = self.client.get(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'view'), obj=instance)
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertEqual(response.status_code, self._retrieve_error_code)

    def check_create_permissions(self, user, create_data, password):
        user = self.login(user, password)
        response = self.client.post(self.model_class.get_list_url(), create_data, HTTP_ACCEPT='application/json',
                                    format='json')
        has_perm = user.has_perm(create_perm_str(self.model_class(), 'add'))
        if has_perm:
            self.assertResponseOk(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_update_permissions(self, user, instance, password):
        user = self.login(user, password)
        serialized = self.serializer_class(instance)
        response = self.client.put(instance.get_absolute_url(), serialized.data, HTTP_ACCEPT='application/json',
                                   format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'change'))
        if has_perm:
            self.assertResponseAccepted(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_destroy_permissions(self, user, instance, password):
        user = self.login(user, password)
        response = self.client.delete(instance.get_absolute_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'delete'))
        if has_perm:
            self.assertResponseDeleted(response)
        else:
            self.assertResponsePermissionDenied(response)

    def check_list_permissions(self, user, instance, password):
        user = self.login(user, password)
        list_response = self.client.get(instance.get_list_url(), HTTP_ACCEPT='application/json', format='json')
        has_perm = user.has_perm(create_perm_str(instance, 'view'))
        if has_perm:
            self.assertResponseOk(list_response)
            is_visible_in_list = len(list_response.data['results']) > 0
        else:
            self.assertResponsePermissionDenied(list_response)
            is_visible_in_list = False

        has_instance_perm = user.has_perm(create_perm_str(instance, 'view'), instance)
        self.assertEqual(is_visible_in_list, has_instance_perm)

    def check_retrieve(self):
        for user in self.representative_users:
            self.check_retrieve_permissions(user, self.instance, self.user_factory.password)
            assign_perm(create_perm_str(self.instance, 'view'), user_or_group=user, obj=self.instance)
            self.check_retrieve_permissions(user, self.instance, self.user_factory.password)

    def check_destroy(self):
        for user in self.representative_users:
            instance = self.instance_factory.create()
            self.check_destroy_permissions(user, instance, self.user_factory.password)
            assign_perm(create_perm_str(self.instance, 'delete'), user_or_group=user, obj=instance)
            self.check_destroy_permissions(user, instance, self.user_factory.password)

    def check_update(self):
        for user in self.representative_users:
            instance = self.instance_factory.create()
            self.check_update_permissions(user, instance, self.user_factory.password)
            assign_perm(create_perm_str(self.instance, 'change'), user_or_group=user, obj=instance)
            self.check_update_permissions(user, instance, self.user_factory.password)

    def check_create(self):
        for user in self.representative_users:
            create_data = self.instance_factory.data_for_create_request()
            self.check_create_permissions(user, create_data, self.user_factory.password)

    def check_list(self):
        for user in self.representative_users:
            self.check_list_permissions(user, self.instance, self.user_factory.password)
            assign_perm(create_perm_str(self.instance, 'view'), user_or_group=user, obj=self.instance)
            self.check_list_permissions(user, self.instance, self.user_factory.password)
