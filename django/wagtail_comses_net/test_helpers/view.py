from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from guardian.shortcuts import assign_perm
from django.urls import reverse
from django.shortcuts import get_object_or_404
from hypothesis.extra import django as hypothesis_django
from hypothesis import strategies as st
from django.contrib.auth.models import Group, User, Permission


def letters(min_size=1, max_size=20):
    return st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Lu')), min_size=min_size, max_size=max_size)


class ViewSetTestCase(hypothesis_django.TestCase):
    model_cls = None
    modelviewset_cls = None
    serializer_cls = None
    detail_url_name = None
    list_url_name = None

    all_permissions = {'add': True, 'change': True, 'delete': True, 'view': True}
    read_permission = {'view': True}
    no_permission = {'add': False, 'change': False, 'delete': False, 'view': False}
    action_http_map = {'add': 'post', 'change': 'put', 'delete': 'delete', 'view': 'get'}
    action_success_map = {'add': status.HTTP_201_CREATED, 'change': status.HTTP_200_OK,
                          'delete': status.HTTP_204_NO_CONTENT, 'view': status.HTTP_200_OK}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def is_db_action_permitted(self, user: User, action: str, obj):
        perm = self.make_perm(action)
        return user.has_perm(perm) and user.has_perm(perm, obj)

    def get_serialized_data(self, obj):
        return self.serializer_cls(obj).data

    def check_response_status_code(self, action, response, permitted):
        if permitted:
            status_code = self.action_success_map[action]
            self.assertEqual(response.status_code, status_code)
        else:
            self.assertGreaterEqual(response.status_code, 400)
            self.assertLess(response.status_code, 500)

    def _create_response(self, action, data, user):
        http_method = self.action_http_map[action]
        request_factory = getattr(self.factory, http_method)
        request = request_factory(reverse(self.detail_url_name, kwargs={'pk': data['id']}), data=data, format='json')
        force_authenticate(request, user)
        response = self.modelviewset_cls.as_view(
            {'put': 'update', 'get': 'retrieve', 'post': 'create', 'delete': 'destroy'})(request, pk=data['id'])
        return response

    def create_add_response(self, user: User, obj):
        data = self.get_serialized_data(obj)
        data.pop('id')

        http_method = self.action_http_map['add']
        request_factory = getattr(self.factory, http_method)
        request = request_factory(reverse(self.list_url_name), data=data, format='json')
        force_authenticate(request, user)
        response = self.modelviewset_cls.as_view(
            {'put': 'update', 'get': 'retrieve', 'post': 'create', 'delete': 'destroy'})(request)
        return response

    def create_change_response(self, user: User, obj):
        data = self.get_serialized_data(obj)
        return self._create_response('change', data, user)

    def create_delete_response(self, user: User, obj):
        data = self.get_serialized_data(obj)
        return self._create_response('delete', data, user)

    def create_view_response(self, user: User, obj):
        data = self.get_serialized_data(obj)
        return self._create_response('view', data, user)

    def create_response(self, action: str, user: User, obj):
        return getattr(self, 'create_' + action + '_response')(user, obj)

    def _check_authorization(self, user: User, obj, action: str, permitted: bool):
        self.assertEqual(self.is_db_action_permitted(user, action, obj), permitted)
        self.check_response_status_code(action, self.create_response(action, user, obj), permitted)

    def make_perm(self, action):
        return "{}.{}_{}".format(self.model_cls._meta.app_label, action, self.model_cls._meta.model_name)

    @staticmethod
    def create_member_group_and_add_user(user):
        members, created = Group.objects.get_or_create(name='Members')
        members.permissions = Permission.objects.exclude(codename__startswith='view_')
        user.groups.add(members)
        # Bust the cache and recheck authorizations
        user = get_object_or_404(user._meta.model, pk=user.id)
        return user

    def check_authorization(self, action, profile, obj):
        user = profile.user
        if not user.is_active:
            self._check_authorization(user, obj, action, False)
            return

        if user.is_superuser:
            self._check_authorization(user, obj, action, True)
            return

        if obj.submitter == user:
            if action == 'view':
                # User is not part of edit group originally so doesn't have edit permission to own data
                self._check_authorization(user, obj, action, True)
            else:
                self._check_authorization(user, obj, action, False)
                user = self.create_member_group_and_add_user(user)
                self._check_authorization(user, obj, action, True)
            return

        if action == 'view' and obj.live:
            self._check_authorization(user, obj, action, True)
            return

        self._check_authorization(user, obj, action, False)
        assign_perm(action + '_' + obj._meta.model_name, user, obj)
        user = self.create_member_group_and_add_user(user)
        self._check_authorization(user, obj, action, True)