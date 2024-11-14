from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework import status

from core.models import SpamModeration
from core.tests.base import BaseModelTestCase, EventFactory, JobFactory
from library.tests.base import CodebaseFactory


class SpamModerationAPITestCase(BaseModelTestCase):
    def setUp(self):
        super().setUp()

        self.api_key = settings.LLM_SPAM_CHECK_API_KEY
        self.client = APIClient()
        self.client.default_format = "json"

        self.job_factory = JobFactory(submitter=self.user)
        self.event_factory = EventFactory(submitter=self.user)

        today = timezone.now()

        # Create test objects

        self.job = self.job_factory.create(
            application_deadline=today + timedelta(days=30),
            title="Test Job",
            description="Job Description",
        )

        self.event = self.event_factory.create(
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=14),
            title="Test Event",
        )

        codebase_factory = CodebaseFactory(submitter=self.user)
        self.codebase = codebase_factory.create(
            title="Test Codebase", description="Codebase Description"
        )

        # Create SpamModeration objects
        self.job_spam = SpamModeration.objects.create(
            content_object=self.job, status=SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        self.event_spam = SpamModeration.objects.create(
            content_object=self.event, status=SpamModeration.Status.SCHEDULED_FOR_CHECK
        )
        self.codebase_spam = SpamModeration.objects.create(
            content_object=self.codebase,
            status=SpamModeration.Status.SCHEDULED_FOR_CHECK,
        )

    def test_authentication_required(self):
        # Test without authentication
        response = self.client.get("/api/spam/get-latest-batch/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post("/api/spam/update/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with incorrect API key
        self.client.credentials(HTTP_X_API_KEY="wrong_key")

        response = self.client.get("/api/spam/get-latest-batch/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(
            "/api/spam/update/", {"object_id": 1, "is_spam": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with correct API key
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        response = self.client.get("/api/spam/get-latest-batch/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            "/api/spam/update/", {"object_id": 1, "is_spam": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_latest_spam_batch(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        response = self.client.get("/api/spam/get-latest-batch/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 3)  # We expect 3 items in the batch

        # Check if all content types are present
        content_types = [item["contentType"] for item in data]
        self.assertIn("job", content_types)
        self.assertIn("event", content_types)
        self.assertIn("codebase", content_types)

        # Check structure of a job item
        job_item = next(item for item in data if item["contentType"] == "job")
        self.assertIn("id", job_item)
        self.assertIn("objectId", job_item)
        self.assertIn("contentObject", job_item)
        self.assertIn("title", job_item["contentObject"])
        self.assertIn("description", job_item["contentObject"])

    def test_get_latest_spam_batch_empty(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        # Change all SpamModeration statuses
        SpamModeration.objects.all().update(status=SpamModeration.Status.SPAM)

        response = self.client.get("/api/spam/get-latest-batch/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)  # We expect an empty list

    def test_update_spam_moderation_success(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        data = {
            "object_id": self.job_spam.id,
            "is_spam": True,
            "spam_indicators": ["indicator1", "indicator2"],
            "reasoning": "Test reasoning",
            "confidence": 0.9,
        }

        response = self.client.post("/api/spam/update/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["message"], "SpamModeration updated successfully"
        )

        # Check if SpamModeration object was updated correctly
        updated_spam = SpamModeration.objects.get(id=self.job_spam.id)
        self.assertEqual(updated_spam.status, SpamModeration.Status.SPAM_LIKELY)
        self.assertEqual(updated_spam.detection_method, "LLM")
        self.assertEqual(
            updated_spam.detection_details["spam_indicators"],
            ["indicator1", "indicator2"],
        )
        self.assertEqual(updated_spam.detection_details["reasoning"], "Test reasoning")
        self.assertEqual(updated_spam.detection_details["confidence"], 0.9)

        # Check if related content object was updated
        self.assertTrue(updated_spam.content_object.is_marked_spam)

    def test_update_spam_moderation_not_spam(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        data = {
            "object_id": self.event_spam.id,
            "is_spam": False,
            "reasoning": "Not spam reasoning",
            "confidence": 0.8,
        }

        response = self.client.post("/api/spam/update/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_spam = SpamModeration.objects.get(id=self.event_spam.id)
        self.assertEqual(updated_spam.status, SpamModeration.Status.NOT_SPAM_LIKELY)
        self.assertFalse(updated_spam.content_object.is_marked_spam)

    def test_update_spam_moderation_not_found(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        data = {"object_id": 99999, "is_spam": True}  # Non-existent ID

        response = self.client.post("/api/spam/update/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_spam_moderation_invalid_data(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        data = {
            "object_id": self.codebase_spam.id,
            # Missing required 'is_spam' field
        }

        response = self.client.post("/api/spam/update/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_spam_moderation_partial_update(self):
        self.client.credentials(HTTP_X_API_KEY=self.api_key)

        data = {
            "object_id": self.job_spam.id,
            "is_spam": True,
            # Only providing partial data
        }

        response = self.client.post("/api/spam/update/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_spam = SpamModeration.objects.get(id=self.job_spam.id)

        self.assertEqual(updated_spam.status, SpamModeration.Status.SPAM_LIKELY)
        self.assertEqual(updated_spam.detection_details.get("spam_indicators"), [])
        self.assertEqual(updated_spam.detection_details.get("reasoning"), "")
        self.assertIsNone(updated_spam.detection_details.get("confidence"))
