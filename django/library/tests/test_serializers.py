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
        User.objects.get_or_create(username=username)
        return {
            "institution_name": "SHESC",
            "institution_url": "http://shesc.asu.edu",
            "username": username,
        }

    def create_raw_contributor(self, raw_user):
        return {
            "affiliations": [],
            "email": "a@b.com",
            "family_name": "Bar",
            "given_name": "Foo",
            "middle_name": "",
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
            "user": user.pk,
            "release": release.pk,
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
            "user": user.pk,
            "release": release.pk,
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
