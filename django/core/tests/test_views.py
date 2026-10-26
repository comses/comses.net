import logging
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from rest_framework.test import APIClient

from django.urls import reverse
from django.test import TestCase

from .base import create_test_user, update_index, JobFactory, EventFactory
from .permissions_base import BaseViewSetTestCase
from core.views import EventViewSet, JobViewSet, rest_exception_handler
from core.models import Job, Event, SpamModeration, ComsesGroups

logger = logging.getLogger(__name__)


class RestExceptionHandlerTestCase(TestCase):
    @patch("core.views.page_not_found")
    def test_html_renderer_uses_html_not_found_response(self, page_not_found):
        expected_response = object()
        page_not_found.return_value = expected_response
        request = SimpleNamespace(accepted_renderer=SimpleNamespace(format="html"))
        exception = Http404()

        response = rest_exception_handler(exception, {"request": request})

        self.assertIs(response, expected_response)
        page_not_found.assert_called_once_with(
            request, exception, context={"request": request}
        )


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
        response = self.client.get(reverse("core:job-detail", kwargs={"pk": self.job.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        update_index()
        response = self.client.get(reverse("core:job-list"))
        self.assertEqual(response.status_code, 200)


class EventPageRenderTestCase(TestCase):
    client_class = APIClient

    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.event_factory = EventFactory(submitter=self.submitter)
        self.event = self.event_factory.create()

    def test_detail(self):
        response = self.client.get(reverse("core:event-detail", kwargs={"pk": self.event.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        update_index()
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
        self.profile.personal_url = "https://geocities.com/{}".format(self.submitter.username)
        self.profile.save()

    def test_detail(self):
        response = self.client.get(reverse("core:profile-detail", kwargs={"pk": self.submitter.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        update_index()
        response = self.client.get(reverse("core:profile-list"))
        self.assertEqual(response.status_code, 200)


class SpamDetectionTestCase(BaseViewSetTestCase):
    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.moderator = self.user_factory.create(username="moderator")
        ComsesGroups.MODERATOR.add(self.moderator)
        self.superuser = self.user_factory.create(username="admin", is_superuser=True)
        self.client.login(username=self.submitter.username, password=self.user_factory.password)
        self.event_factory = EventFactory(submitter=self.submitter)
        self.job_factory = JobFactory(submitter=self.submitter)

    def tearDown(self):
        self.client.logout()

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
        self.assertFalse(event.is_marked_spam)
        self.assertIsNone(event.spam_moderation)
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event.refresh_from_db()
        # non-moderators cannot mark content as spam
        self.assertEqual(response.status_code, 403)
        self.assertFalse(event.is_marked_spam)
        # check moderator
        self.client.login(username=self.moderator.username, password=self.user_factory.password)
        self.assertTrue(ComsesGroups.is_moderator(self.moderator))
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event.refresh_from_db()
        self.assertTrue(event.is_marked_spam)
        self.assertIsNotNone(event.spam_moderation)
        event.mark_not_spam(self.moderator)
        event.refresh_from_db()
        self.assertFalse(event.is_marked_spam)
        self.assertIsNotNone(event.spam_moderation)
        # check superuser
        self.client.login(username=self.superuser.username, password=self.user_factory.password)
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            data,
            HTTP_ACCEPT="application/json",
            format="json",
        )
        event.refresh_from_db()
        self.assertTrue(event.is_marked_spam)
        self.assertIsNotNone(event.spam_moderation)
        self.assertEqual(event.spam_moderation.status, SpamModeration.Status.SPAM)

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
        self.assertIsNone(event.spam_moderation)

    def test_exclude_spam_from_public_views(self):
        event = self.event_factory.create(title="pool cleaning in Salzburg", submitter=self.submitter)
        self.client.login(username=self.moderator.username, password=self.user_factory.password)
        response = self.client.post(
            reverse("core:event-mark-spam", kwargs={"pk": event.id}),
            {"notes": "Spam"},
            format="json",
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.get(reverse("core:event-list"))
        self.assertNotContains(response, event.title)
