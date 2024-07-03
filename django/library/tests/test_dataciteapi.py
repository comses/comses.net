import logging

# import pathlib
# import semver
# import uuid

from django.conf import settings

# from django.contrib.auth.models import AnonymousUser
# from rest_framework.exceptions import ValidationError

from core.tests.base import UserFactory, BaseModelTestCase
from .base import (
    CodebaseFactory,
    ContributorFactory,
    ReleaseContributorFactory,
    ReleaseSetup,
)
from ..models import Codebase, CodebaseRelease, License
from library.doi import DataCiteApi, doi_matches_pattern

logger = logging.getLogger(__name__)


class DataCiteApiTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()

        # determine current server's datacite prefix
        env = settings.DEPLOYMENT_ENVIRONMENT
        self.DATACITE_PREFIX = (
            "10.82853" if env.is_development or env.is_staging else "10.25937"
        )

        self.dc = DataCiteApi(dry_run=False)

        # create a codebase and 3 releases
        self.cb = Codebase.objects.create(
            title="Test codebase",
            description="Test codebase description",
            identifier="cb",
            submitter=self.user,
        )
        self.release1 = self.cb.create_release()
        self.release2 = self.cb.create_release(
            {"title": self.cb.title + " (2nd release)"}
        )
        self.release3 = self.cb.create_release(
            {"title": self.cb.title + " (3rd release)"}
        )

        # assign fake DOIs for releases
        self.release1.doi = self.DATACITE_PREFIX + "/release1"
        self.release2.doi = self.DATACITE_PREFIX + "release2"
        self.release3.doi = self.DATACITE_PREFIX + "release3"

    def test_mint_new_doi_for_codebase(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        reply = self.dc.mint_new_doi_for_codebase(self.cb)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))

    def test_update_metadata_for_codebase(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        self.title = self.title + " (updated)"
        # reply = self.dc.update_metadata_for_codebase(self)
        # self.assertTrue(DataCiteApi._is_same_metadata(reply, self.datacite.metadata))
        self.assertTrue(self.dc.update_metadata_for_codebase(self))

    def test_mint_new_doi_for_release(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        reply = self.dc.mint_new_doi_for_release(self.release1)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))

    def test_update_metadata_for_release(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        self.release1.title = self.release1.title + " (updated)"
        # reply = self.dc.update_metadata_for_release(self.release1)
        # self.assertTrue(
        #    DataCiteApi._is_same_metadata(reply, self.release1.datacite.metadata)
        # )
        self.assertTrue(self.dc.update_metadata_for_release(self.release1))
