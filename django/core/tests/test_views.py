import logging

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .base import create_test_user, EventFactory, JobFactory
from .permissions_base import BaseViewSetTestCase

from core.models import ComsesGroups, Event, Job, SpamModeration
from core.views import EventViewSet, JobViewSet

logger = logging.getLogger(__name__)


class JobViewSetTestCase(BaseViewSetTestCase):
    _view = JobViewSet

    def setUp(self):
        self.submitter = self.user_factory.create(username="submitter")
        self.instance_factory = JobFactory(submitter=self.submitter)
        self.create_representative_users(self.submitter)
        self.instance = self.instance_factory.create()

    def test_retrieve(self):
        self.check_retrieve()

    def test_destroy(self):
        self.check_destroy()

    def test_update(self):
        self.check_update()

    def test_create(self):
        self.check_create()

    def test_list(self):
        self.check_list()


class EventViewSetTestCase(BaseViewSetTestCase):
    _view = EventViewSet

    def setUp(self):
        submitter = self.user_factory.create(username="submitter")
        self.instance_factory = EventFactory(submitter=submitter)
        self.create_representative_users(submitter)
        self.instance = self.instance_factory.create()

    def test_retrieve(self):
        self.check_retrieve()

    def test_destroy(self):
        self.check_destroy()

    def test_update(self):
        self.check_update()

    def test_create(self):
        self.check_create()

    def test_list(self):
        self.check_list()


class JobPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.job_factory = JobFactory(submitter=self.submitter)
        self.job = self.job_factory.create()

    def test_detail(self):
        response = self.client.get(
            reverse("core:job-detail", kwargs={"pk": self.job.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse("core:job-list"))
        self.assertEqual(response.status_code, 200)


class EventPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.event_factory = EventFactory(submitter=self.submitter)
        self.event = self.event_factory.create()

    def test_detail(self):
        response = self.client.get(
            reverse("core:event-detail", kwargs={"pk": self.event.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse("core:event-list"))
        self.assertEqual(response.status_code, 200)

    def test_calendar(self):
        response = self.client.get(reverse("core:event-calendar"))
        self.assertEqual(response.status_code, 200)


class ProfilePageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.submitter, self.user_factory = create_test_user()
        self.profile = self.submitter.member_profile
        self.profile.personal_url = "https://geocities.com/{}".format(
            self.submitter.username
        )
        self.profile.save()

    def test_detail(self):
        response = self.client.get(
            reverse("core:profile-detail", kwargs={"pk": self.submitter.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse("core:profile-list"))
        self.assertEqual(response.status_code, 200)


class SpamDetectionTestCase(BaseViewSetTestCase):

    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.moderator = self.user_factory.create(username="moderator")
        ComsesGroups.MODERATOR.add(self.moderator)
        self.superuser = self.user_factory.create(username="admin", is_superuser=True)
        self.client.login(
            username=self.submitter.username, password=self.user_factory.password
        )
        self.event_factory = EventFactory(submitter=self.submitter)
        self.job_factory = JobFactory(submitter=self.submitter)

    def tearDown(self):
        self.client.logout()

    def test_event_creation_with_honeypot_spam(self):
        data = self.event_factory.get_request_data(honeypot_value="spammy content")
        response = self.client.post(
            reverse("core:event-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        self.assertResponseCreated(response)
        event = Event.objects.get(title=data["title"])

        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(
            event.spam_moderation.status, SpamModeration.Status.SPAM_LIKELY
        )
        self.assertEqual(event.spam_moderation.detection_method, "honeypot")
        self.assertTrue(event.is_marked_spam)

    def test_job_creation_with_timer_spam(self):
        # FIXME: should incorporate how long a typical request takes to resolve
        data = self.job_factory.get_request_data(
            elapsed_time=settings.SPAM_LIKELY_SECONDS_THRESHOLD - 2
        )
        response = self.client.post(
            reverse("core:job-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        self.assertResponseCreated(response)
        job = Job.objects.get(title=data["title"])

        self.assertIsNotNone(job.spam_moderation)
        self.assertEqual(job.spam_moderation.status, SpamModeration.Status.SPAM_LIKELY)
        self.assertEqual(job.spam_moderation.detection_method, "form_submit_time")
        self.assertTrue(job.is_marked_spam)

    def test_mark_spam(self):
        data = self.event_factory.get_request_data()
        # create Job or Event (ModeratedContent)
        response = self.client.post(
            reverse("core:event-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event = Event.objects.get(title=data["title"])
        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(
            event.spam_moderation.status, SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        # by default, all created objects will have is_marked_spam = False unless spam_moderation.status is explicitly SPAM or SPAM_LIKELY
        self.assertFalse(event.is_marked_spam)

        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )

        event.refresh_from_db()
        # non-moderators cannot mark content as spam
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(
            event.spam_moderation.status, SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        self.assertFalse(event.is_marked_spam)

        # check moderator
        self.client.login(
            username=self.moderator.username, password=self.user_factory.password
        )
        self.assertTrue(ComsesGroups.is_moderator(self.moderator))
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event.refresh_from_db()
        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertTrue(event.is_marked_spam)

        event.mark_not_spam(self.moderator)
        event.refresh_from_db()

        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(event.spam_moderation.status, SpamModeration.Status.NOT_SPAM)
        self.assertFalse(event.is_marked_spam)

        # check superuser
        self.client.login(
            username=self.superuser.username, password=self.user_factory.password
        )
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event.refresh_from_db()

        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(event.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertTrue(event.is_marked_spam)

    def test_event_creation_without_spam(self):
        data = self.event_factory.get_request_data()
        response = self.client.post(
            reverse("core:event-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        self.assertResponseCreated(response)
        event = Event.objects.get(title=data["title"])

        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(
            event.spam_moderation.status, SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        self.assertFalse(event.is_marked_spam)

    def test_job_update_with_spam(self):
        data = self.job_factory.get_request_data()
        response = self.client.post(
            reverse("core:job-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        self.assertResponseCreated(response)
        job = Job.objects.get(title=data["title"])

        self.assertIsNotNone(job.spam_moderation)
        self.assertEqual(
            job.spam_moderation.status, SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        self.assertFalse(job.is_marked_spam)

        data = self.job_factory.get_request_data(
            honeypot_value="spammy content",
            elapsed_time=settings.SPAM_LIKELY_SECONDS_THRESHOLD + 1,
        )
        response = self.client.put(
            job.get_absolute_url(),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        job.refresh_from_db()

        self.assertIsNotNone(job.spam_moderation)
        self.assertEqual(job.spam_moderation.status, SpamModeration.Status.SPAM_LIKELY)
        self.assertEqual(job.spam_moderation.detection_method, "honeypot")
        self.assertTrue(job.is_marked_spam)

    def test_exclude_spam_from_public_views(self):
        data = self.event_factory.get_request_data(honeypot_value="spammy content")
        response = self.client.post(
            reverse("core:event-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        public_url = reverse("core:event-list")
        response = self.client.get(public_url)
        self.assertNotContains(response, data["title"])
