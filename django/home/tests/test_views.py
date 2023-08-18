import logging

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from django.urls import reverse
from django.test import TestCase

from core.tests.base import UserFactory

logger = logging.getLogger(__name__)


class WagtailAdminLoginTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(is_superuser=True)
        self.staff = self.user_factory.create(is_staff=True)

    def assertLoginStatusCodeMatchForUser(self, user, status_code):
        success = self.client.login(
            username=user.username, password=self.user_factory.password
        )
        if success:
            response = self.client.get(reverse("wagtailadmin_home"))
            self.assertEqual(response.status_code, status_code)
            return response
        else:
            raise ValueError("login for user {} failed".format(user))

    def test_regular_login(self):
        regular_user = self.user_factory.create()
        # default behavior for wagtail admin login failed is a 302 redirect to the login page
        response = self.assertLoginStatusCodeMatchForUser(
            regular_user, status.HTTP_302_FOUND
        )
        message = response.context["message"]
        self.assertEqual(message, "You do not have permission to access the admin")

    def test_superuser_login(self):
        superuser = self.user_factory.create(is_superuser=True)
        self.assertLoginStatusCodeMatchForUser(superuser, status.HTTP_200_OK)

    def test_staff_login(self):
        staff = self.user_factory.create(is_staff=True)
        response = self.assertLoginStatusCodeMatchForUser(staff, status.HTTP_302_FOUND)
        message = response.context["message"]
        self.assertEqual(message, "You do not have permission to access the admin")

    def test_access_admin_login(self):
        content_type = ContentType.objects.get(model="admin")
        permission = Permission.objects.get(
            content_type=content_type, codename="access_admin"
        )
        access_admin_user = self.user_factory.create()
        access_admin_user.user_permissions.add(permission)
        self.assertLoginStatusCodeMatchForUser(access_admin_user, status.HTTP_200_OK)
