import json
import logging
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

import requests
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.test import TestCase, override_settings
from django.urls import reverse
from huey.contrib.djhuey import HUEY
from rest_framework.test import APIClient, APITestCase

from core.models import ComsesGroups, Event, Job, MemberProfile, SpamDetectionSettings, SpamModeration
from core.tasks import check_spam, queue_spam_check
from core.views import EventViewSet, JobViewSet, rest_exception_handler

from .base import EventFactory, JobFactory, create_test_user, update_index
from .permissions_base import BaseViewSetTestCase

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
        self.profile.personal_url = f"https://geocities.com/{self.submitter.username}"
        self.profile.save()

    def test_detail(self):
        response = self.client.get(reverse("core:profile-detail", kwargs={"pk": self.submitter.id}))
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        update_index()
        response = self.client.get(reverse("core:profile-list"))
        self.assertEqual(response.status_code, 200)


def provider_response(probability, provider="asu"):
    if provider == "asu":
        body = {"verdicts": {"spam": {"type": "boolean", "probabilities": {"true": probability}}}}
    else:
        body = {"result": {"answers": {"spam": {"type": "noul", "noul": probability}}}}
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(body).encode()
    return response


@override_settings(VOYAGER_AI_API_KEY="asu-key", CLOUDFLARE_ACCOUNT_ID="account", CLOUDFLARE_AI_API_TOKEN="cf-token")
class SpamDetectionModelTestCase(APITestCase):
    def setUp(self):
        self.submitter, self.user_factory = create_test_user(username="submitter")
        self.moderator = self.user_factory.create(username="moderator")
        self.client.force_login(self.submitter)
        self.client.credentials(HTTP_ACCEPT="application/json")
        self.job_factory = JobFactory(submitter=self.submitter)
        self.configure()
        self.addCleanup(setattr, HUEY, "immediate", HUEY.immediate)
        HUEY.immediate = True
        # Only the external HTTP boundary is mocked; saves, tasks and moderation are real.
        patcher = mock.patch("core.spam.requests.post", return_value=provider_response(0.97))
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def configure(self, **kwargs):
        config = SpamDetectionSettings.load()
        for key, value in {"enabled": True, **kwargs}.items():
            setattr(config, key, value)
        config.save()

    def save_job(self, title, job=None):
        data = self.job_factory.get_request_data(title=title)
        with self.captureOnCommitCallbacks(execute=True):
            if job:
                response = self.client.put(job.get_absolute_url(), data, format="json")
                self.assertEqual(response.status_code, 200, response.content)
            else:
                response = self.client.post(reverse("core:job-list"), data, format="json")
                self.assertEqual(response.status_code, 201, response.content)
        return Job.objects.get(title=title)

    def test_submission_decisions_control_public_listing(self):
        spam = self.save_job("Unwanted advertisement")
        self.post.return_value = provider_response(0.02)
        legitimate = self.save_job("Postdoc in agent-based modeling")
        self.assertTrue(spam.is_marked_spam)
        self.assertFalse(legitimate.is_marked_spam)
        self.assertEqual(spam.spam_moderation.status, SpamModeration.Status.SPAM)
        self.assertEqual(legitimate.spam_moderation.status, SpamModeration.Status.NOT_SPAM)
        self.assertIsNone(spam.spam_moderation.reviewer)
        request = self.post.call_args_list[0].kwargs["json"]
        self.assertEqual(request["questions"]["spam"]["type"], "boolean")
        self.assertEqual(request["state"]["title"], spam.title)
        self.assertNotIn(self.submitter.email, json.dumps(request))
        self.assertEqual(spam.spam_moderation.detection_details["input"], request["state"])
        update_index()
        self.client.logout()
        response = self.client.get(reverse("core:job-list"), HTTP_ACCEPT="application/json")
        self.assertContains(response, legitimate.title)
        self.assertNotContains(response, spam.title)

    def test_submission_edits_do_not_queue_another_check(self):
        self.post.return_value = provider_response(0.02)
        job = self.save_job("Postdoc in agent-based modeling")
        self.post.reset_mock()
        self.post.return_value = provider_response(0.97)
        job = self.save_job("Edited postdoc advertisement", job=job)
        self.save_job(job.title, job=job)
        self.assertFalse(job.is_marked_spam)
        self.post.assert_not_called()

    def test_rolled_back_submission_never_calls_provider(self):
        data = self.job_factory.get_request_data(title="Rolled back submission")
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesRegex(RuntimeError, "roll back"):
                with transaction.atomic():
                    response = self.client.post(reverse("core:job-list"), data, format="json")
                    self.assertEqual(response.status_code, 201, response.content)
                    self.post.assert_not_called()
                    raise RuntimeError("roll back")
        self.assertFalse(Job.objects.filter(title=data["title"]).exists())
        self.post.assert_not_called()

    def test_duplicate_task_does_not_repeat_completed_check(self):
        job = self.save_job("Unwanted advertisement")
        moderation_id = job.spam_moderation_id
        self.post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            queue_spam_check(job)
        job.refresh_from_db()
        self.post.assert_not_called()
        self.assertEqual(job.spam_moderation_id, moderation_id)
        self.assertEqual(SpamModeration.objects.count(), 1)

    def test_moderator_decision_during_detection_wins(self):
        job = self.job_factory.create()

        def review_while_waiting(*args, **kwargs):
            job.mark_spam(detection_method="manual", reviewer=self.moderator)
            job.mark_not_spam(self.moderator)
            return provider_response(0.97)

        self.post.side_effect = review_while_waiting
        with self.captureOnCommitCallbacks(execute=True):
            queue_spam_check(job)
        job.refresh_from_db()
        self.post.assert_called_once()
        self.assertFalse(job.is_marked_spam)
        self.assertEqual(job.spam_moderation.reviewer, self.moderator)
        self.post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            queue_spam_check(job)
        self.post.assert_not_called()

    def test_disabled(self):
        self.configure(enabled=False)
        job = self.save_job("Unwanted advertisement")
        self.assertIsNone(job.spam_moderation)
        self.post.assert_not_called()

    def test_primary_timeout_uses_fallback_threshold(self):
        self.post.side_effect = [requests.Timeout("read timed out"), provider_response(0.85, "cloudflare")]
        self.configure(fallback_threshold=0.9)
        job = self.save_job("Borderline advertisement")
        self.assertFalse(job.is_marked_spam)
        moderation = job.spam_moderation
        self.assertEqual(moderation.detection_method, "cloudflare/clef-omni")
        self.assertEqual(moderation.threshold, 0.9)
        self.assertEqual(moderation.detection_details["fallback_from"][0]["model"], "asu/gemma4-31b-it")
        primary, fallback = self.post.call_args_list
        self.assertEqual(primary.kwargs["timeout"], 15)
        self.assertEqual(fallback.kwargs["json"]["questions"]["spam"]["type"], "noul")

    def test_invalid_primary_probability_uses_fallback(self):
        for invalid in [None, "0.9", True, -0.1, 1.1, float("nan")]:
            with self.subTest(probability=invalid):
                self.post.side_effect = [provider_response(invalid), provider_response(0.97, "cloudflare")]
                job = self.save_job(f"Invalid probability {invalid}")
                self.assertIsNotNone(job.spam_moderation)
                self.assertEqual(job.spam_moderation.detection_method, "cloudflare/clef-omni")
                self.assertTrue(job.is_marked_spam)

    def test_provider_outage_leaves_content_unclassified_for_retry(self):
        job = self.job_factory.create()
        content_type_id = ContentType.objects.get_for_model(job).pk
        self.post.side_effect = requests.Timeout("provider unavailable")
        with self.assertRaises(requests.Timeout):
            check_spam.call_local(content_type_id, job.pk)
        job.refresh_from_db()
        self.assertIsNone(job.spam_moderation)
        self.assertFalse(job.is_marked_spam)
        self.assertEqual(self.post.call_count, 2)
        self.post.side_effect = None
        check_spam.call_local(content_type_id, job.pk)
        job.refresh_from_db()
        self.assertTrue(job.is_marked_spam)

    def test_edit_during_initial_check_retries_current_content(self):
        job = self.job_factory.create()
        content_type_id = ContentType.objects.get_for_model(job).pk

        def edit_while_waiting(*args, **kwargs):
            Job.objects.filter(pk=job.pk).update(title="Corrected advertisement")
            return provider_response(0.97)

        self.post.side_effect = edit_while_waiting
        with self.assertRaisesRegex(RuntimeError, "Content changed"):
            check_spam.call_local(content_type_id, job.pk)
        job.refresh_from_db()
        self.assertIsNone(job.spam_moderation)
        self.post.side_effect = None
        self.post.return_value = provider_response(0.02)
        check_spam.call_local(content_type_id, job.pk)
        job.refresh_from_db()
        self.assertFalse(job.is_marked_spam)
        self.assertEqual(job.spam_moderation.detection_details["input"]["title"], "Corrected advertisement")

    @override_settings(VOYAGER_AI_API_KEY="")
    def test_skips_primary_without_api_key(self):
        self.post.return_value = provider_response(0.97, "cloudflare")
        job = self.save_job("Unwanted advertisement")
        self.assertEqual(job.spam_moderation.detection_method, "cloudflare/clef-omni")
        self.post.assert_called_once()
        self.assertNotIn("fallback_from", job.spam_moderation.detection_details)

    @override_settings(VOYAGER_AI_API_KEY="", CLOUDFLARE_AI_API_TOKEN="")
    def test_skips_check_without_api_keys(self):
        job = self.save_job("Unwanted advertisement")
        self.assertIsNone(job.spam_moderation)
        self.post.assert_not_called()

    def test_profile_edits_update_decision_and_visibility(self):
        ComsesGroups.initialize()
        data = {
            "given_name": "Test",
            "family_name": "Member",
            "email": self.submitter.email,
            "full_member": False,
            "tags": [],
            "affiliations": [],
            "degrees": [],
            "industry": "",
            "bio": "Unwanted advertisement",
            "research_interests": "",
            "personal_url": "",
            "professional_url": "",
        }
        url = reverse("core:profile-detail", kwargs={"pk": self.submitter.pk})
        for probability, bio, hidden in [(0.97, "Unwanted advertisement", True), (0.02, "I study ABM.", False)]:
            with self.subTest(bio=bio):
                self.post.return_value = provider_response(probability)
                data["bio"] = bio
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.put(url, data, format="json")
                self.assertEqual(response.status_code, 200, response.content)
                profile = MemberProfile.objects.get(user=self.submitter)
                self.assertEqual(profile.is_marked_spam, hidden)
                self.assertEqual(profile.spam_moderation.detection_details["input"]["bio"], bio)
                update_index()
                response = self.client.get(reverse("core:profile-list"), HTTP_ACCEPT="application/json")
                if hidden:
                    self.assertNotContains(response, self.submitter.username)
                else:
                    self.assertContains(response, self.submitter.username)
        self.assertEqual(self.post.call_count, 2)


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
        legitimate = self.event_factory.create(title="Agent-based modeling workshop")
        event.mark_spam(detection_method="manual", reviewer=self.moderator)
        update_index()
        self.client.logout()
        response = self.client.get(reverse("core:event-list"), HTTP_ACCEPT="application/json")
        self.assertContains(response, legitimate.title)
        self.assertNotContains(response, event.title)
