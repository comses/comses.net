from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


class SocialAccountLoginViewTestCase(TestCase):
    fixtures = ["core/fixtures/test/socialapps.json"]

    @override_settings(SOCIALACCOUNT_LOGIN_ON_GET=False)
    def test_orcid_login_confirmation_page(self):
        response = self.client.get(reverse("orcid_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "third party account from Orcid.org")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    @override_settings(SOCIALACCOUNT_LOGIN_ON_GET=False)
    def test_normal_provider_login_still_redirects(self):
        for provider, host in (("github", "github.com"), ("orcid", "sandbox.orcid.org")):
            with self.subTest(provider=provider):
                response = self.client.post(reverse(f"{provider}_login"))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(f"https://{host}/"))


@override_settings(EXTERNAL_AUTH_ENABLED=False)
class RecoveryExternalAuthTests(TestCase):
    fixtures = ["core/fixtures/test/socialapps.json"]

    def setUp(self):
        SocialApp.objects.update(client_id="restored-test-client", secret="restored-test-secret")

    def test_restored_providers_cannot_start_connect_or_complete_login(self):
        self.assertTrue(SocialApp.objects.exists())
        # A callback must be rejected before token exchange, even with stale state.
        with patch("requests.sessions.Session.request", side_effect=AssertionError("outbound request")):
            for provider in ("github", "orcid"):
                for suffix in ("login", "callback"):
                    for method in ("get", "post"):
                        with self.subTest(provider=provider, suffix=suffix, method=method):
                            response = getattr(self.client, method)(
                                reverse(f"{provider}_{suffix}"),
                                {"process": "connect", "code": "unused", "state": "unused"},
                            )
                            self.assertEqual(response.status_code, 403)
                            self.assertNotIn("Location", response)

    def test_other_external_auth_routes_are_blocked(self):
        for name in ("socialaccount_connections", "core:discourse-sso", "core:librarian-sso"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    @override_settings(EXTERNAL_AUTH_ENABLED="False")
    def test_truthy_string_does_not_enable_external_auth(self):
        response = self.client.post(reverse("github_login"))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Location", response)

    def test_local_login_logout_remain_available(self):
        user = User.objects.create_user("recovery-test", "recovery@example.invalid", "local-test-password")
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
        page = self.client.get(reverse("account_login"))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'action="/accounts/github/login/')
        self.assertNotContains(page, 'action="/accounts/orcid/login/')
        self.assertContains(page, "External sign-in is disabled on this deployment")
        response = self.client.post(
            reverse("account_login"), {"login": user.username, "password": "local-test-password"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        response = self.client.post(reverse("account_logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
