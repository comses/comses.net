from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "account-email-tests"}},
)
class AccountEmailViewTests(TestCase):
    def setUp(self):
        # Database rollback does not clear allauth's email verification rate limits.
        cache.clear()
        self.user = User.objects.create_user("email-test", "current@example.org", "test-password")
        self.current_email = EmailAddress.objects.create(
            user=self.user, email=self.user.email, primary=True, verified=True
        )
        self.url = reverse("account_email")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('account_login')}?next={self.url}", fetch_redirect_response=False)

    def test_current_email_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Ensure the project Jinja override is used instead of allauth's bundled Django template.
        self.assertEqual(response.template_name, ["account/email_change.jinja"])
        self.assertContains(response, self.current_email.email)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="action_add"')
        self.assertNotContains(response, 'name="action_send"')

    def test_pending_email_page(self):
        EmailAddress.objects.create(user=self.user, email="pending@example.org", verified=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.current_email.email)
        self.assertContains(response, "pending@example.org")
        self.assertContains(response, 'name="action_send"')
        self.assertContains(response, 'name="action_remove"')

    def test_unverified_current_email_can_resend_verification(self):
        self.current_email.verified = False
        self.current_email.save(update_fields=["verified"])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.current_email.email)
        self.assertContains(response, 'name="action_send"')
        self.assertNotContains(response, 'name="action_remove"')

    def test_add_email_creates_pending_address_and_sends_verification(self):
        new_email = "pending@example.org"

        response = self.client.post(self.url, {"email": new_email, "action_add": ""})

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        pending = EmailAddress.objects.get(user=self.user, email=new_email)
        self.assertFalse(pending.primary)
        self.assertFalse(pending.verified)
        self.current_email.refresh_from_db()
        self.user.refresh_from_db()
        self.assertTrue(self.current_email.primary)
        self.assertEqual(self.user.email, self.current_email.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [new_email])

    def test_resend_pending_email_sends_verification(self):
        pending = EmailAddress.objects.create(user=self.user, email="pending@example.org", verified=False)

        response = self.client.post(self.url, {"email": pending.email, "action_send": ""})

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        pending.refresh_from_db()
        self.assertFalse(pending.verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [pending.email])

        # A repeat request succeeds without sending another email during the cooldown.
        response = self.client.post(self.url, {"email": pending.email, "action_send": ""})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)

    def test_cannot_resend_verification_for_another_users_email(self):
        other_user = User.objects.create_user("other-email-test", "other@example.org", "test-password")
        other_email = EmailAddress.objects.create(user=other_user, email=other_user.email, verified=False)

        response = self.client.post(self.url, {"email": other_email.email, "action_send": ""})

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)
        other_email.refresh_from_db()
        self.assertFalse(other_email.verified)

    def test_invalid_email_renders_errors(self):
        response = self.client.post(self.url, {"email": "invalid", "action_add": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address.")
        self.current_email.refresh_from_db()
        self.assertTrue(self.current_email.primary)
        self.assertEqual(self.user.emailaddress_set.count(), 1)

    def test_cancel_pending_change(self):
        pending = EmailAddress.objects.create(user=self.user, email="pending@example.org", verified=False)
        response = self.client.post(self.url, {"email": pending.email, "action_remove": ""}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EmailAddress.objects.filter(pk=pending.pk).exists())
        self.assertContains(response, self.current_email.email)
        self.assertNotContains(response, 'name="action_remove"')
