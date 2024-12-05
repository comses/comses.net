import logging


from core.tests.base import BaseModelTestCase
from .base import ReleaseSetup
from ..doi import DataCiteApi
from ..models import Codebase

logger = logging.getLogger(__name__)


class DataCiteApiTest(BaseModelTestCase):
    """
    Should exercise the DataCiteApi but currently can't test full integration with datacite sandbox.
    Would also continue to "pollute" our sandbox repository on every test run.

    FIXME: add better tests over is_metadata_equivalent with actual datacite metadata + responses
    """

    def setUp(self):
        super().setUp()

        self.api = DataCiteApi(dry_run=False)

        # create a codebase (which do NOT automatically create a required release)
        self.codebase = Codebase.objects.create(
            title="Test codebase with releases for DataCite",
            description="Test codebase description",
            identifier="test.cb.101",
            submitter=self.user,
        )
        self.release = ReleaseSetup.setUpPublishableDraftRelease(self.codebase)
        self.release.publish()

    """
    FIXME: DataCite test repository does not allow localhost urls so minting DOIs won't work
    unless we mock out the permanent_url to a non-localhost value in test settings

    def test_mint_new_doi_for_codebase(self):
        self.assertTrue(self.api.is_datacite_available())
        # verify datacite prefix logic ?
        # self.assertEqual(self.DATACITE_PREFIX, settings.DATACITE_PREFIX)

    def test_update_metadata_for_codebase(self):
        self.assertTrue(self.api.is_datacite_available())
        self.codebase.title = self.codebase.title + " (updated)"
        # self.assertTrue(self.dc.update_doi_metadata(self.cb))

    def test_mint_new_doi_for_release(self):
        self.assertTrue(self.api.is_datacite_available())
        release = self.codebase.releases.first()
        log, ok = self.api.mint_public_doi(release)
        self.assertEquals(log.http_status, 200, "should have successfully minted a DOI")
        self.assertTrue(self.api.doi_matches_pattern(doi))

    def test_update_metadata_for_release(self):
        self.assertTrue(self.api.is_datacite_available())
        release = self.codebase.releases.first()
        release.release_notes.raw += " (updated)"
        # FIXME: won't work until we mock out the permanent_url to a non-localhost value in test settings
        # self.assertTrue(self.api.update_doi_metadata(release))
    """

    def test_is_metadata_equivalent_publication_year(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [{"name": "John Doe"}],
        }
        datacite_metadata = {
            "title": "Sample Title",
            "publicationYear": 2023,
            "creators": [{"name": "John Doe"}],
        }
        self.assertTrue(
            DataCiteApi.is_metadata_equivalent(comses_metadata, datacite_metadata)
        )

    def test_is_metadata_equivalent_different_title(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [{"name": "John Doe"}],
        }
        datacite_metadata = {
            "title": "Different Title",
            "publicationYear": 2023,
            "creators": [{"name": "John Doe"}],
        }
        self.assertFalse(
            DataCiteApi.is_metadata_equivalent(comses_metadata, datacite_metadata)
        )

    def test_is_metadata_equivalent_missing_keys(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [{"name": "John Doe"}],
        }
        datacite_metadata = {
            "title": "Sample Title",
            "creators": [{"name": "John Doe"}],
        }
        self.assertFalse(
            DataCiteApi.is_metadata_equivalent(comses_metadata, datacite_metadata)
        )

    def test_is_same_metadata_empty_values(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": None,
            "creators": [{"name": "John Doe"}],
        }
        dc_metadata = {
            "title": "Sample Title",
            "publicationYear": 0,
            "creators": [{"name": "John Doe"}],
        }
        self.assertTrue(
            DataCiteApi.is_metadata_equivalent(comses_metadata, dc_metadata)
        )

    def test_is_metadata_equivalent_nested_dict(self):
        sent_data = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [
                {
                    "name": "John Doe",
                    "affiliation": {
                        "ror_id": "https://ror.org/12345",
                        "name": "University of Earth",
                    },
                }
            ],
        }
        received_data = {
            "title": "Sample Title",
            "publicationYear": 2023,
            "creators": [
                {
                    "name": "John Doe",
                    "affiliation": {
                        "ror_id": "https://ror.org/12345",
                        "name": "University of Earth",
                    },
                }
            ],
        }
        self.assertTrue(DataCiteApi.is_metadata_equivalent(sent_data, received_data))

    def test_is_metadata_equivalent_list_ordering(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [{"name": "John Doe"}, {"name": "Jane Doe"}],
        }
        dc_metadata = {
            "title": "Sample Title",
            "publicationYear": 2023,
            "creators": [{"name": "Jane Doe"}, {"name": "John Doe"}],
        }
        self.assertTrue(
            DataCiteApi.is_metadata_equivalent(comses_metadata, dc_metadata)
        )

    def test_is_same_metadata_different_nested_list(self):
        comses_metadata = {
            "title": "Sample Title",
            "publicationYear": "2023",
            "creators": [{"name": "John Doe"}, {"name": "Jane Doe"}],
        }
        dc_metadata = {
            "title": "Sample Title",
            "publicationYear": 2023,
            "creators": [{"name": "John Doe"}, {"name": "Jane Smith"}],
        }
        self.assertFalse(
            DataCiteApi.is_metadata_equivalent(comses_metadata, dc_metadata)
        )
