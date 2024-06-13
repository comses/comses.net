from django.contrib.auth.models import User
import rest_framework.exceptions as rf

from core.tests.base import BaseModelTestCase
from ..models import Codebase
from ..serializers import (
    ContributorSerializer,
    ReleaseContributorSerializer,
    DownloadRequestSerializer,
)


class SerializerTestCase(BaseModelTestCase):
    def create_raw_user(self, username="foo.bar"):
        user, _ = User.objects.get_or_create(username=username)
        return {
            "username": user.username,
            "id": user.id,
        }

    def create_raw_contributor(
        self,
        raw_user,
        email="a@b.com",
        family_name="Bar",
        given_name="Foo",
        middle_name="Middle",
    ):
        return {
            "affiliations": [],
            "email": email,
            "family_name": family_name,
            "given_name": given_name,
            "middle_name": middle_name,
            "type": "person",
            "user": raw_user,
        }

    def create_raw_release_contributor(self, raw_contributor, index=None):
        raw_release_contributor = {
            "contributor": raw_contributor,
            "include_in_citation": True,
            "roles": ["author"],
        }

        if index is None:
            return raw_release_contributor
        else:
            raw_release_contributor["index"] = index
            return raw_release_contributor

    def create_codebase(
        self,
        user=None,
        title="Test codebase",
        description="Test codebase description",
        identifier="0xdeadbeef",
    ):
        if user is None:
            user = self.user
        codebase = Codebase.objects.create(
            title=title, description=description, identifier=identifier, submitter=user
        )
        codebase.create_release(submitter=user)
        return codebase

    def test_contributor_save(self):
        raw_contributor = self.create_raw_contributor(self.create_raw_user())
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid(raise_exception=True)
        contributor = contributor_serializer.save()
        self.assertEqual(contributor.email, raw_contributor["email"])

    def test_release_contributor_save(self):
        codebase = self.create_codebase(identifier="1")
        codebase_release = codebase.releases.last()

        raw_release_contributor = self.create_raw_release_contributor(
            raw_contributor=self.create_raw_contributor(self.create_raw_user()), index=0
        )
        release_contributor_serializer = ReleaseContributorSerializer(
            data=raw_release_contributor, context={"release_id": codebase_release.id}
        )
        release_contributor_serializer.is_valid(raise_exception=True)
        release_contributor = release_contributor_serializer.save()
        self.assertEqual(release_contributor.roles, raw_release_contributor["roles"])

    def test_nouser_contributor_save(self):
        raw_contributor = self.create_raw_contributor(None, email="nouser@example.com")
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid(raise_exception=True)
        contributor = contributor_serializer.save()
        self.assertEqual(contributor.email, raw_contributor["email"])

    def test_multiple_release_contributor_save(self):
        codebase = Codebase.objects.create(
            title="Test codebase",
            description="Test codebase description",
            identifier="1",
            submitter=self.user,
        )
        codebase_release = codebase.create_release(
            initialize=False, submitter=self.user
        )

        raw_contributor1 = self.create_raw_contributor(self.create_raw_user("foo"))
        raw_contributor2 = self.create_raw_contributor(self.create_raw_user("bar"))

        raw_release_contributors = [
            self.create_raw_release_contributor(
                raw_contributor=raw_contributor1, index=1
            ),
            self.create_raw_release_contributor(
                raw_contributor=raw_contributor2, index=None
            ),
        ]

        release_contributors_serializer = ReleaseContributorSerializer(
            many=True,
            data=raw_release_contributors,
            context={"release_id": codebase_release.id},
        )
        release_contributors_serializer.is_valid(raise_exception=True)
        release_contributors = release_contributors_serializer.save()

        self.assertEqual(release_contributors[0].index, 0)
        self.assertEqual(release_contributors[1].index, 1)

    def test_download_request_create(self):
        codebase = self.create_codebase(title="Download Request Codebase")
        release = codebase.releases.last()
        user = self.user
        data = {
            "ip_address": "127.0.0.1",
            "referrer": "https://comses.net",
            "user": user.id,
            "release": release.id,
            "reason": "policy",
            "industry": "university",
            "affiliation": {"name": "ASU", "url": "https://asu.edu/"},
            "save_to_profile": True,
        }
        download_request = DownloadRequestSerializer(data=data)
        download_request.is_valid()
        crs = download_request.save()
        user.refresh_from_db()
        self.assertEqual(data["industry"], user.member_profile.industry)
        self.assertTrue(data["affiliation"] in user.member_profile.affiliations)
        for attr in ("ip_address", "referrer", "reason"):
            self.assertEqual(data[attr], getattr(crs, attr))
        self.assertEqual(user, crs.user)
        self.assertEqual(release, crs.release)

    def test_invalid_download_request_raises_validation_error(self):
        codebase = self.create_codebase(title="Download Request Codebase 2")
        release = codebase.releases.last()
        user = self.user
        data = {
            "ip_address": "127.0.0.1",
            "referrer": "https://comses.net",
            "user": user.id,
            "release": release.id,
            "reason": "policy",
            "industry": "university",
            "affiliation": {"name": "ASU", "url": "www.foo.org", "ror_id": "foo8j8sd"},
            "save_to_profile": True,
        }
        download_request = DownloadRequestSerializer(data=data)
        download_request.is_valid()
        with self.assertRaises(rf.ValidationError):
            download_request.save()

    def test_multiple_release_contributor_same_user_raises_validation_error(self):
        codebase = Codebase.objects.create(
            title="Test codebase",
            description="Test codebase description",
            identifier="1",
            submitter=self.user,
        )
        codebase_release = codebase.create_release(
            initialize=False, submitter=self.user
        )

        raw_contributor = self.create_raw_contributor(
            raw_user=self.create_raw_user("foo")
        )
        raw_contributor2 = raw_contributor.copy()
        raw_contributor2["family_name"] = "Zar"
        raw_release_contributors = [
            self.create_raw_release_contributor(
                index=1, raw_contributor=raw_contributor
            ),
            self.create_raw_release_contributor(
                index=None, raw_contributor=raw_contributor2
            ),
        ]

        release_contributors_serializer = ReleaseContributorSerializer(
            many=True,
            data=raw_release_contributors,
            context={"release_id": codebase_release.id},
        )
        with self.assertRaises(rf.ValidationError):
            release_contributors_serializer.is_valid(raise_exception=True)

    def test_get_existing_contributor_given_user(self):
        # correctly matches a contributor to a user
        raw_user = self.create_raw_user(username="contrib123")
        raw_contributor = self.create_raw_contributor(raw_user)
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid()
        contributor_serializer.save()
        _, existing_contributor = contributor_serializer.get_existing_contributor(
            raw_contributor
        )
        self.assertEqual(existing_contributor.user.id, raw_user["id"])

        # contributor is none (needs to be created) when user is given but no matching contributor
        raw_user = self.create_raw_user(username="contrib456")
        raw_contributor = self.create_raw_contributor(
            raw_user, email="contrib456@hotmail.com"
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        _, existing_contributor = contributor_serializer.get_existing_contributor(
            raw_contributor
        )
        self.assertIsNone(existing_contributor)

    def test_get_existing_contributor_given_email(self):
        # correctly matches a contributor with the same email
        email = "johnprine@aol.com"
        raw_contributor = self.create_raw_contributor(
            raw_user=None, email=email, family_name="Prine", given_name="John"
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid()
        contributor = contributor_serializer.save()
        _, found_contributor = contributor_serializer.get_existing_contributor(
            {"email": email}
        )
        self.assertEqual(contributor.id, found_contributor.id)

        # contributor is none (needs to be created) when email match is not found
        # we dont want to overwrite the email even if a name match exists
        email = "johnprine@yahoo.com"
        raw_contributor = self.create_raw_contributor(
            raw_user=None, email=email, family_name="Prine", given_name="John"
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        _, found_contributor = contributor_serializer.get_existing_contributor(
            raw_contributor
        )
        self.assertIsNone(found_contributor)

    def test_get_existing_contributor_given_name(self):
        # correctly matches a contributor with the same name if no user or email matches can be found
        given_name = "Robert"
        family_name = "Fripp"
        raw_contributor = self.create_raw_contributor(
            raw_user=None, email="", family_name=family_name, given_name=given_name
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid()
        contributor = contributor_serializer.save()
        _, found_contributor = contributor_serializer.get_existing_contributor(
            {"given_name": given_name, "family_name": family_name}
        )
        self.assertEqual(contributor.id, found_contributor.id)

        # contributor is none (needs to be created) when name match is not found
        raw_contributor = self.create_raw_contributor(
            raw_user=None, email="", family_name="Thom", given_name="Yorke"
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        _, found_contributor = contributor_serializer.get_existing_contributor(
            raw_contributor
        )
        self.assertIsNone(found_contributor)

        # check that we only match contributors that do not have an email in this case
        raw_contributor = self.create_raw_contributor(
            raw_user=None,
            email="differentfripp@aol.com",
            family_name=family_name,
            given_name=given_name,
        )
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        _, found_contributor = contributor_serializer.get_existing_contributor(
            raw_contributor
        )
        self.assertIsNone(found_contributor)
