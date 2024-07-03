import logging, string, uuid

from django.conf import settings
from django.utils.crypto import get_random_string

from core.tests.base import BaseModelTestCase
from ..models import Codebase, CodebaseRelease
from library.doi import DataCiteApi, doi_matches_pattern

logger = logging.getLogger(__name__)


class DataCiteApiTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        allowed_chars = string.ascii_lowercase + string.digits

        self.dc = DataCiteApi(dry_run=False)

        # determine current server's datacite prefix
        env = settings.DEPLOY_ENVIRONMENT
        self.DATACITE_PREFIX = (
            "10.82853" if env.is_development or env.is_staging else "10.25937"
        )

        # create a codebase (which do NOT automatically create a release)
        self.cb = Codebase.objects.create(
            title="Test codebase and releases to Datacite",
            description="Test codebase description",
            identifier=uuid.uuid4(),
            submitter=self.user,
        )

        # create 3 releases with fake DOIs to test the parent/child/sibling
        for i in [1, 2, 3]:
            r = self.cb.create_release()
            r.doi = (
                self.DATACITE_PREFIX + "/test-" + get_random_string(4, allowed_chars)
            )
            r.save()

    def test_mint_new_doi_for_codebase(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        reply = self.dc.mint_new_doi_for_codebase(self.cb)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))
        self.cb.doi = reply
        self.cb.save()

    def test_update_metadata_for_codebase(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        self.cb.title = self.cb.title + " (updated)"
        # reply = self.dc.update_metadata_for_codebase(self)
        # self.assertTrue(DataCiteApi._is_same_metadata(reply, self.datacite.metadata))
        self.assertTrue(self.dc.update_metadata_for_codebase(self))
        self.cb.save()

    def test_mint_new_doi_for_release(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        release = self.cb.releases.first()
        reply = self.dc.mint_new_doi_for_release(release)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))
        release.doi = reply
        release.save()

    """
    Note updating the title will update title for codebase and all releases;
    so instead we'll update the release note field for the first release
    """
    def test_update_metadata_for_release(self):
        self.assertTrue(self.dc.heartbeat())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        release = self.cb.releases.first()
        release.release_notes = release.release_notes + " (updated)"
        # reply = self.dc.update_metadata_for_release(self.release1)
        # self.assertTrue(
        #    DataCiteApi._is_same_metadata(reply, self.release1.datacite.metadata)
        # )
        self.assertTrue(self.dc.update_metadata_for_release(release))
        release.save()
