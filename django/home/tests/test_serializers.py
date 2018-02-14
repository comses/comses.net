from datetime import datetime, timedelta
from unittest import TestCase

from rest_framework.exceptions import ValidationError

from core.models import MemberProfile, ComsesGroups, Institution
from core.tests.base import UserFactory
from core.serializers import EventSerializer
from home.serializers import MemberProfileSerializer
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


class MemberProfileSerializerTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.user = self.user_factory.create(username='foo')
        self.user.first_name = 'Foo'
        self.user.last_name = 'Bar'
        ComsesGroups.initialize()

    def test_cannot_downgrade_membership(self):
        membership_profile = self.user.member_profile
        self.assertFalse(membership_profile.full_member)

        institution = Institution(url='https://foo.org', name='Foo Institute')
        institution.save()
        membership_profile.institution = institution
        membership_profile.save()
        membership_profile_data = MemberProfileSerializer(membership_profile).data

        # Make user a full down member
        membership_profile_data['full_member'] = True
        serializer = MemberProfileSerializer(instance=membership_profile,
                                             data=membership_profile_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership_profile = MemberProfile.objects.get(id=membership_profile.id)
        self.assertTrue(membership_profile.full_member)

        # Unsuccessfully attempt to downgrade membership status
        membership_profile_data['full_member'] = False
        serializer = MemberProfileSerializer(instance=membership_profile,
                                             data=membership_profile_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership_profile = MemberProfile.objects.get(id=membership_profile.id)
        self.assertTrue(membership_profile.full_member)