import json
import logging

from django.conf import settings
from rest_framework.test import APIClient

from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from core.tests.base import UserFactory
from core.tests.permissions_base import BaseViewSetTestCase
from core.views import EventViewSet, JobViewSet
from core.models import Job, Event
from .base import JobFactory, EventFactory

logger = logging.getLogger(__name__)


class JobViewSetTestCase(BaseViewSetTestCase):
    _view = JobViewSet

    def setUp(self):
        self.user_factory = UserFactory()
        submitter = self.user_factory.create(username="submitter")
        self.instance_factory = JobFactory(submitter=submitter)
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


class EventViewSetTestCase(BaseViewSetTestCase):
    _view = EventViewSet

    def setUp(self):
        self.user_factory = UserFactory()
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
        user_factory = UserFactory()
        self.submitter = user_factory.create(username="submitter")
        job_factory = JobFactory(submitter=self.submitter)
        self.job = job_factory.create()

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
        user_factory = UserFactory()
        self.submitter = user_factory.create(username="submitter")
        event_factory = EventFactory(submitter=self.submitter)
        self.event = event_factory.create()

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
        user_factory = UserFactory()
        self.submitter = user_factory.create()
        self.profile = self.submitter.member_profile
        self.profile.personal_url = "https://geocities.com/{}".format(
            self.submitter.username
        )
        self.profile.save()

    def test_detail(self):
        response = self.client.get(
            reverse("core:profile-detail", kwargs={"pk": self.submitter.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        response = self.client.get(reverse("core:profile-list"))
        self.assertEqual(response.status_code, 200)


class SpamDetectionTestCase(BaseViewSetTestCase):

    def setUp(self):
        self.user_factory = UserFactory()
        self.submitter = self.user_factory.create(username="submitter")
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
        self.assertTrue(event.is_marked_spam)
        self.assertIsNotNone(event.spam_content)
        self.assertEqual(event.spam_content.detection_method, "honeypot")

    def test_job_creation_with_timer_spam(self):
        data = self.job_factory.get_request_data(
            seconds_delta=settings.SPAM_LIKELY_SECONDS_THRESHOLD - 1
        )
        response = self.client.post(
            reverse("core:job-list"),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        self.assertResponseCreated(response)
        job = Job.objects.get(title=data["title"])
        self.assertTrue(job.is_marked_spam)
        self.assertIsNotNone(job.spam_content)
        self.assertEqual(job.spam_content.detection_method, "form_submit_time")

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
        self.assertFalse(event.is_marked_spam)
        self.assertIsNone(event.spam_content)

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
        self.assertFalse(job.is_marked_spam)
        self.assertIsNone(job.spam_content)
        data = self.job_factory.get_request_data(
            honeypot_value="spammy content",
            seconds_delta=settings.SPAM_LIKELY_SECONDS_THRESHOLD + 1,
        )
        response = self.client.put(
            job.get_absolute_url(),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        job.refresh_from_db()
        self.assertTrue(job.is_marked_spam)
        self.assertIsNotNone(job.spam_content)
        self.assertEqual(job.spam_content.detection_method, "honeypot")

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
