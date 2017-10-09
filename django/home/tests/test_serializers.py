from datetime import datetime, timedelta
from unittest import TestCase

from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory
from home.serializers import EventSerializer
from home.tests.base import EventFactory


class EventSerializerTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.user = self.user_factory.create()
        self.event_factory = EventFactory(submitter=self.user)

    def test_start_date_lth_end_date(self):
        event = self.event_factory.create_unsaved()
        dt = datetime.now() + timedelta(days=1)
        event.start_date = dt
        event.end_date = dt

        serialized_event = EventSerializer(event).data
        with self.assertRaises(ValidationError):
            deserialized_event = EventSerializer(data=serialized_event)
            deserialized_event.is_valid(raise_exception=True)

        event.end_date = event.start_date + timedelta(days=1)
        serialized_event = EventSerializer(event).data
        deserialized_event = EventSerializer(data=serialized_event)
        deserialized_event.is_valid(raise_exception=True)
