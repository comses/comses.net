from django.test import TestCase
from django.urls import reverse

from core.models import SpamModeration
from core.tests.base import JobFactory, UserFactory, EventFactory
from curator.models import TagCleanup
from curator.wagtail_hooks import TagCleanupPermissionHelper


class ProcessTagCleanupsTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(is_superuser=True)
        self.user = self.user_factory.create()
        self.tag_cleanups = TagCleanup.objects.bulk_create(
            [
                TagCleanup(old_name="foo", new_name="bar"),
                TagCleanup(old_name="foo", new_name="baz"),
            ]
        )

    def test_process_tagcleanups_permission(self):
        self.client.login(
            username=self.user.username, password=self.user_factory.password
        )

        # Users without process_tagcleanup permission should not be able to use the route
        response = self.client.post(TagCleanup.process_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            TagCleanup.objects.filter(transaction_id__isnull=True).count(), 2
        )

        # Superusers can call the process route to process tag cleanups
        self.client.login(
            username=self.superuser.username, password=self.user_factory.password
        )
        response = self.client.post(
            TagCleanup.process_url(), data={"action": "process"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            TagCleanup.objects.filter(transaction_id__isnull=True).count(), 0
        )

    def test_no_delete_permission_on_inactive_tagcleanups(self):
        tag_cleanup = TagCleanup.objects.get(new_name="bar")
        ph = TagCleanupPermissionHelper(TagCleanup)
        self.assertIsNone(tag_cleanup.transaction_id)
        self.assertTrue(ph.user_can_delete_obj(self.superuser, tag_cleanup))
        TagCleanup.objects.process()
        tag_cleanup = TagCleanup.objects.get(new_name="bar")
        self.assertIsNotNone(tag_cleanup.transaction_id)
        self.assertFalse(ph.user_can_delete_obj(self.superuser, tag_cleanup))


class SpamAdminViewTestCase(TestCase):

    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(username="admin", is_superuser=True)
        self.submitter = self.user_factory.create(username="submitter")
        self.client.login(
            username=self.superuser.username, password=self.user_factory.password
        )
        self.event_factory = EventFactory(submitter=self.submitter)
        self.job_factory = JobFactory(submitter=self.submitter)
        self.event = self.event_factory.create(
            title="pool cleaning in Salzburg", submitter=self.submitter
        )
        SpamModeration.objects.create(
            content_object=self.event,
            object_id=self.event.id,
            detection_method="honeypot",
            detection_details={"honeypot_value": "and hot tubs"},
        )
        self.event.refresh_from_db()

    def tearDown(self):
        self.client.logout()

    def test_admin_confirm_spam(self):
        url = reverse("curator:confirm_spam", args=[self.event.spam_moderation.id])
        response = self.client.get(url)
        self.event.refresh_from_db()
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertTrue(self.event.is_marked_spam)
        self.assertTrue(self.event.submitter.is_active)

    def test_admin_reject_spam(self):
        url = reverse("curator:reject_spam", args=[self.event.spam_moderation.id])
        response = self.client.get(url)
        self.event.refresh_from_db()
        self.assertEqual(
            self.event.spam_moderation.status, SpamModeration.Status.NOT_SPAM
        )
        self.assertFalse(self.event.is_marked_spam)

    def test_admin_confirm_spam_deactivate_user(self):
        url = reverse("curator:confirm_spam", args=[self.event.spam_moderation.id])
        response = self.client.get(url + "?deactivate_user=true")
        self.event.refresh_from_db()
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertTrue(self.event.is_marked_spam)
        self.assertFalse(self.event.submitter.is_active)
