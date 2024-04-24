import logging

from django.conf import settings
from django.utils.crypto import get_random_string

from .base import ReleaseSetup
from core.tests.base import BaseModelTestCase
from ..models import Codebase
from library.doi import DataCiteApi

logger = logging.getLogger(__name__)

"""
The skelton python tests here need much more work but should pass successfully.
See
https://docs.google.com/document/d/19-FdJcLdNYpMW4rgc85EzBq1xuI3HqZ3PVagJ-1nXlM/edit#heading=h.73fadsz9a3mr
for the overall goal.
"""


class DataCiteApiTest(BaseModelTestCase):
    """
    Create a codebase with an initial release
    """

    def setUp(self):
        super().setUp()

        self.dc = DataCiteApi(dry_run=False)

        # determine current server's datacite prefix
        env = settings.DEPLOY_ENVIRONMENT
        self.DATACITE_PREFIX = (
            "10.82853" if env.is_development or env.is_staging else "10.25937"
        )

        # create a codebase (which do NOT automatically create a required release)
        self.cb = Codebase.objects.create(
            title="Test codebase and releases to Datacite",
            description="Test codebase description",
            identifier="cb",
            submitter=self.user,
        )

        """
        allowed_chars = string.ascii_lowercase + string.digits
        # create 3 releases with fake DOIs to test the parent/child/sibling
        for i in [1, 2, 3]:
            r = self.cb.create_release()
            r.doi = (
                self.DATACITE_PREFIX + "/test-" + get_random_string(4, allowed_chars)
            )
            r.save()
        """
        self.create_release_ready_to_mint_doi()

    """
    FIXME: when the issue with the creators metadata is solved, then this
    function needs to be completed.  See
    https://docs.google.com/document/d/19-FdJcLdNYpMW4rgc85EzBq1xuI3HqZ3PVagJ-1nXlM/edit#heading=h.qu5a82ym9f0r
    for description of the problem with creators metadata
    """

    def test_mint_new_doi_for_codebase(self):
        self.assertTrue(self.dc.is_datacite_available())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        """
        reply = self.dc.mint_public_doi(self.cb)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))
        self.cb.doi = reply
        self.cb.save()
        """

    """
    Test by updating codebase title
    """

    def test_update_metadata_for_codebase(self):
        self.assertTrue(self.dc.is_datacite_available())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        self.cb.title = self.cb.title + " (updated)"
        # self.assertTrue(self.dc.update_doi_metadata(self.cb))

    def test_mint_new_doi_for_release(self):
        self.assertTrue(self.dc.is_datacite_available())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        release = self.cb.releases.first()
        """
        reply = self.dc.mint_public_doi(release)
        self.assertContains(reply, self.DATACITE_PREFIX + "/")
        self.assertTrue(doi_matches_pattern(reply))
        release.doi = reply
        release.save()
        """

    """
    Note updating the title will update title for codebase and all releases;
    so instead we'll update the release note field for the first release
    """

    def test_update_metadata_for_release(self):
        self.assertTrue(self.dc.is_datacite_available())
        self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)
        release = self.cb.releases.first()
        release.release_notes.raw += " (updated)"
        # self.assertTrue(self.dc.update_doi_metadata(release))

    def create_release_ready_to_mint_doi(self):
        """
        following copied from test_models.py but doesn't seem to work here...
        the creators metadata ends up either being empty or 2 test_users...
        not sure if that's the cause of the problem but _validate_metadata()
        fails...
        """
        release = ReleaseSetup.setUpPublishableDraftRelease(self.cb)

        # publish() will call validate_publishable() so don't need to call here
        # release.validate_publishable()
        release.publish()
        # release.save()
        return release
