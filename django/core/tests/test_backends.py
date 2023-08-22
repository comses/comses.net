import logging

from allauth.socialaccount.models import SocialApp
from django.urls import reverse
from django.test import TestCase
from rest_framework.status import HTTP_302_FOUND, HTTP_200_OK

from .base import UserFactory

logger = logging.getLogger(__name__)


class EmailAuthenticationBackendTestCase(TestCase):
    fixtures = ["core/fixtures/test/socialapps.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = "test"
        cls.wrong_password = "bar"
        cls.user_factory = UserFactory(password=cls.password)

    def credentials(self, user, password=None):
        if not password:
            password = self.password
        return {"login": user.username, "password": password}

    def login(self, user, password):
        return self.client.post(
            path=reverse("account_login"), data=self.credentials(user, password)
        )

    def login_with_email(self, user, password):
        return self.client.post(
            path=reverse("account_login"), data=self.credentials(user, password)
        )

    def check_authentication_failed(self, user, password):
        authorized = self.client.login(username=user.username, password=password)
        self.assertFalse(authorized)

    def check_authentication_succeeded(self, user, expected=True):
        authenticated = self.client.login(
            username=user.username, password=self.password
        )
        self.assertEqual(authenticated, expected)

    def _check_response_status_code(self, user, password, status_code):
        self.client.get(reverse("account_login"))
        response = self.login(user, password)
        self.assertEqual(response.status_code, status_code)
        self.client.logout()
        response_with_email = self.login_with_email(user, password)
        self.assertEqual(response_with_email.status_code, status_code)

    def check_response_200(self, user, password=None):
        self._check_response_status_code(user, password, HTTP_200_OK)

    def check_response_302(self, user, password=None):
        self._check_response_status_code(user, password, HTTP_302_FOUND)

    def test_email_authentication(self):
        deactivated_user = self.user_factory.create(is_active=False)
        self.check_response_302(deactivated_user)
        self.check_authentication_succeeded(deactivated_user, False)

        deactivated_superuser = self.user_factory.create(
            is_superuser=True, is_active=False
        )
        self.check_response_302(deactivated_superuser)
        self.check_authentication_succeeded(deactivated_superuser, False)

        user = self.user_factory.create()
        self.check_response_302(user)
        self.check_authentication_succeeded(user)

        superuser = self.user_factory.create(is_superuser=True)
        self.check_response_302(superuser)
        self.check_authentication_succeeded(superuser)

    def test_wrong_password(self):
        logger.debug("all social apps: %s", SocialApp.objects.all())
        deactivated_user = self.user_factory.create(is_active=False)
        self.check_response_200(deactivated_user, password=self.wrong_password)
        self.check_authentication_failed(deactivated_user, password=self.wrong_password)

        deactivated_superuser = self.user_factory.create(
            is_superuser=True, is_active=False
        )
        self.check_response_200(deactivated_superuser, password=self.wrong_password)
        self.check_authentication_failed(
            deactivated_superuser, password=self.wrong_password
        )

        user = self.user_factory.create()
        self.check_response_200(user, password=self.wrong_password)
        self.check_authentication_failed(user, password=self.wrong_password)

        superuser = self.user_factory.create(is_superuser=True)
        self.check_response_200(superuser, password=self.wrong_password)
        self.check_authentication_failed(user, password=self.wrong_password)
