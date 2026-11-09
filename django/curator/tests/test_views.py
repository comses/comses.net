from datetime import timedelta

from core.models import ComsesGroups, SpamModeration
from core.tests.base import EventFactory, JobFactory, UserFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
        self.client.login(username=self.user.username, password=self.user_factory.password)

        # Users without process_tagcleanup permission should not be able to use the route
        response = self.client.post(TagCleanup.process_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(TagCleanup.objects.filter(transaction_id__isnull=True).count(), 2)

        # Superusers can call the process route to process tag cleanups
        self.client.login(username=self.superuser.username, password=self.user_factory.password)
        response = self.client.post(TagCleanup.process_url(), data={"action": "process"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TagCleanup.objects.filter(transaction_id__isnull=True).count(), 0)

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
        self.moderator = self.user_factory.create(username="moderator")
        ComsesGroups.initialize()
        ComsesGroups.MODERATOR.add(self.moderator)
        self.admin_access = Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin")
        self.moderator.user_permissions.add(self.admin_access)
        self.client.force_login(self.moderator)
        self.event_factory = EventFactory(submitter=self.submitter)
        self.job_factory = JobFactory(submitter=self.submitter)
        self.event = self.event_factory.create(title="pool cleaning in Salzburg", submitter=self.submitter)
        SpamModeration.objects.create(
            content_object=self.event,
            object_id=self.event.id,
            detection_method="honeypot",
            detection_details={"honeypot_value": "and hot tubs"},
        )
        self.event.refresh_from_db()

    def tearDown(self):
        self.client.logout()

    def review(self, decision):
        url = reverse("curator_spam:review", args=[self.event.spam_moderation.id])
        response = self.client.post(url, {"decision": decision, "notes": "pool spam"})
        self.event.refresh_from_db()
        self.submitter.refresh_from_db()
        return response

    def test_pages_render(self):
        legitimate = self.job_factory.create(title="Legitimate postdoc opening")
        legitimate.record_spam_check(False, "asu/gemma4-31b-it", {"spam_probability": 0.02, "threshold": 0.8})
        response = self.client.get(reverse("curator_spam:index"))
        self.assertContains(response, "pool cleaning in Salzburg")
        self.assertNotContains(response, legitimate.title)
        response = self.client.get(reverse("curator_spam:index"), {"tab": "all"})
        self.assertContains(response, legitimate.title)
        response = self.client.get(reverse("curator_spam:detail", args=[self.event.spam_moderation.id]))
        self.assertContains(response, "and hot tubs")

    def test_least_certain_first(self):
        for title, p_spam in [("clear postdoc", 0.02), ("borderline workshop", 0.79), ("clear casino", 0.99)]:
            job = self.job_factory.create(title=title, submitter=self.submitter)
            moderation = SpamModeration.objects.create(
                content_object=job,
                object_id=job.id,
                status=SpamModeration.Status.SPAM if p_spam >= 0.8 else SpamModeration.Status.NOT_SPAM,
                detection_method="asu/gemma4-31b-it",
                detection_details={"spam_probability": p_spam, "threshold": 0.8},
            )
            if title == "borderline workshop":
                moderation.review(self.moderator, is_spam=False)
            elif title == "clear postdoc":
                SpamModeration.objects.filter(pk=moderation.pk).update(
                    last_modified=timezone.now() - timedelta(days=31)
                )
        content = self.client.get(reverse("curator_spam:index"), {"tab": "all", "sort": "uncertain"}).content.decode()
        self.assertNotIn("borderline workshop", content)
        self.assertLess(content.index("clear casino"), content.index("clear postdoc"))
        self.assertLess(content.index("clear postdoc"), content.index("pool cleaning in Salzburg"))

    def test_confirm_spam(self):
        self.event.mark_not_spam(self.superuser)
        response = self.review("spam")
        self.assertRedirects(response, reverse("curator_spam:index"), fetch_redirect_response=False)
        self.assertEqual(self.event.spam_moderation.reviewer, self.moderator)
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertEqual(self.event.spam_moderation.notes, "pool spam")
        self.assertTrue(self.event.is_marked_spam)
        self.assertTrue(self.submitter.is_active)

    def test_reject_spam(self):
        response = self.review("not_spam")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.event.spam_moderation.reviewer, self.moderator)
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.NOT_SPAM)
        self.assertFalse(self.event.is_marked_spam)

    def test_confirm_spam_deactivate_user(self):
        self.event.mark_not_spam(self.superuser)
        response = self.review("spam_deactivate")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.event.is_marked_spam)
        self.assertEqual(self.event.spam_moderation.reviewer, self.moderator)
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertFalse(self.submitter.is_active)

    def test_requires_moderator(self):
        self.submitter.user_permissions.add(self.admin_access)
        self.client.force_login(self.submitter)
        for url in [
            reverse("curator_spam:index"),
            reverse("curator_spam:detail", args=[self.event.spam_moderation_id]),
        ]:
            self.assertRedirects(self.client.get(url), reverse("wagtailadmin_home"), fetch_redirect_response=False)
        response = self.review("spam_deactivate")
        self.assertRedirects(response, reverse("wagtailadmin_home"), fetch_redirect_response=False)
        self.assertTrue(self.submitter.is_active)
        self.assertEqual(self.event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertIsNone(self.event.spam_moderation.reviewer)

    def test_review_requires_post(self):
        url = reverse("curator_spam:review", args=[self.event.spam_moderation.id])
        self.assertEqual(self.client.get(url, {"decision": "spam"}).status_code, 405)

    def test_invalid_decision_does_not_change_moderation(self):
        response = self.review("delete")
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.event.spam_moderation.reviewer)
        self.assertTrue(self.event.is_marked_spam)
        self.assertTrue(self.submitter.is_active)

    def test_review_rejects_external_redirect(self):
        url = reverse("curator_spam:review", args=[self.event.spam_moderation_id])
        response = self.client.post(url, {"decision": "not_spam", "next": "https://example.org/"})
        self.assertRedirects(response, reverse("curator_spam:index"), fetch_redirect_response=False)

    def test_review_cannot_deactivate_superuser(self):
        self.event.submitter = self.superuser
        self.event.save()
        response = self.review("spam_deactivate")
        self.assertEqual(response.status_code, 302)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)
        self.assertTrue(self.event.is_marked_spam)


class MarkUserAsSpamTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.superuser = self.user_factory.create(username="admin", is_superuser=True)
        self.target_user = self.user_factory.create(username="spammer")
        self.client.login(username=self.superuser.username, password=self.user_factory.password)

    def tearDown(self):
        self.client.logout()

    def test_mark_user_as_spam_deactivates_and_creates_record(self):
        url = reverse("curator:mark_user_spam", args=[self.target_user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)
        content_type = ContentType.objects.get_for_model(get_user_model())
        spam_moderation = SpamModeration.objects.get(content_type=content_type, object_id=self.target_user.id)
        self.assertEqual(spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertEqual(spam_moderation.reviewer, self.superuser)
        self.assertEqual(spam_moderation.detection_method, "manual")

    def test_mark_user_as_spam_requires_permission(self):
        self.client.logout()
        non_admin = self.user_factory.create(username="nonadmin")
        self.client.login(username=non_admin.username, password=self.user_factory.password)
        url = reverse("curator:mark_user_spam", args=[self.target_user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)

    def test_mark_user_as_spam_rejects_get(self):
        url = reverse("curator:mark_user_spam", args=[self.target_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_mark_user_as_spam_refuses_superuser(self):
        url = reverse("curator:mark_user_spam", args=[self.superuser.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_mark_user_as_spam_idempotent(self):
        url = reverse("curator:mark_user_spam", args=[self.target_user.id])
        self.client.post(url)
        self.client.post(url)
        content_type = ContentType.objects.get_for_model(get_user_model())
        count = SpamModeration.objects.filter(content_type=content_type, object_id=self.target_user.id).count()
        self.assertEqual(count, 1)
