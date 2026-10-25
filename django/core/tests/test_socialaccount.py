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
