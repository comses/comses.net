from datetime import timedelta, date
from django.test import TestCase

from allauth.account.models import EmailAddress
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
        d = date.today() + timedelta(days=1)
        event.start_date = d
        event.end_date = d

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
        self.user = self.user_factory.create()
        self.user.first_name = "Foo"
        self.user.last_name = "Bar"
        ComsesGroups.initialize()

    def test_email_address_update(self):
        other_user = self.user_factory.create()
        other_email = other_user.email

        member_profile = self.user.member_profile
        member_profile.affiliations = [
            {"name": "Foo Institute", "url": "http://foo.org"}
        ]
        member_profile.save()
        email_address = EmailAddress.objects.create(
            user=self.user, email=self.user.email
        )
        email_address.set_as_primary()

        data = MemberProfileSerializer(member_profile).data

        # no change to email address
        serializer = MemberProfileSerializer(instance=member_profile, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(EmailAddress.objects.count(), 1)

        # acceptable address
        data["email"] = "foo2@email.com"
        serializer = MemberProfileSerializer(instance=member_profile, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertTrue(EmailAddress.objects.filter(email=data["email"]).exists())

        # conflicting address
        data["email"] = other_email
        serializer = MemberProfileSerializer(instance=member_profile, data=data)
        serializer.is_valid(raise_exception=True)
        with self.assertRaises(ValidationError):
            serializer.save()

    def test_save_affiliation(self):
        member_profile = self.user.member_profile
        member_profile.save()
        member_profile_data = MemberProfileSerializer(member_profile).data

        # allowed affiliations
        member_profile_data["affiliations"] = [
            {
                "name": "Foo University",
            },
            {"name": "Bar College", "url": "http://bar.org"},
            {
                "name": "FooBar Network",
                "url": "https://foobar.net",
                "acronym": "FBN",
                "ror_id": "https://ror.org/foobar1",
            },
        ]
        serializer = MemberProfileSerializer(
            instance=member_profile, data=member_profile_data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # disallowed affiliations
        member_profile_data["affiliations"] = [
            {"name": "Foo College", "url": "www.foo.edu", "ror_id": "foo8j8sd"}
        ]
        serializer = MemberProfileSerializer(
            instance=member_profile, data=member_profile_data
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # conflicting afffiliations
        member_profile_data["affiliations"] = [
            {"name": "Bar College", "url": "http://bar.org"},
            {
                "name": "Bar College",
                "url": "https://foobar.net",
                "acronym": "BN",
                "ror_id": "https://ror.org/foobar1",
            },
        ]
        serializer = MemberProfileSerializer(
            instance=member_profile, data=member_profile_data
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
            serializer.save()

    def test_cannot_downgrade_membership(self):
        membership_profile = self.user.member_profile
        self.assertFalse(membership_profile.full_member)

        membership_profile.affiliations = [
            {"name": "Foo Institute", "url": "http://foo.org"}
        ]
        membership_profile.save()
        membership_profile_data = MemberProfileSerializer(membership_profile).data

        # Make user a full down member
        membership_profile_data["full_member"] = True
        serializer = MemberProfileSerializer(
            instance=membership_profile, data=membership_profile_data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership_profile = MemberProfile.objects.get(id=membership_profile.id)
        self.assertTrue(membership_profile.full_member)

        # Unsuccessfully attempt to downgrade membership status
        membership_profile_data["full_member"] = False
        serializer = MemberProfileSerializer(
            instance=membership_profile, data=membership_profile_data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership_profile = MemberProfile.objects.get(id=membership_profile.id)
        self.assertTrue(membership_profile.full_member)
