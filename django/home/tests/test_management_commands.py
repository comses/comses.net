from copy import deepcopy
from datetime import date
from unittest.mock import patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from home.models import ComsesDigest


class UpdateDigestArchiveCommandTestCase(TestCase):
    record = {
        "doi": "10.5281/zenodo.1234567",
        "metadata": {
            "title": "CoMSES Digest Vol. 1, Issue 1",
            "journal": {"volume": "1", "issue": "1"},
            "publication_date": "2025-01-15",
        },
        "links": {"latest_html": "https://zenodo.org/records/1234567"},
    }

    def run_command_with_records(self, records):
        with patch(
            "home.management.commands.update_digest_archive.iter_zenodo_records",
            return_value=iter(records),
        ):
            call_command("update_digest_archive")

    def create_existing_digest(self, doi="10.5281/zenodo.9999999"):
        return ComsesDigest.objects.create(
            doi=doi,
            title="Existing digest",
            volume=1,
            issue_number=1,
            publication_date=date(2024, 1, 1),
            url="https://zenodo.org/records/9999999",
        )

    def test_repeated_runs_preserve_database_ids(self):
        self.run_command_with_records([self.record])
        digest_id = ComsesDigest.objects.get(doi=self.record["doi"]).id

        self.run_command_with_records([self.record])

        self.assertEqual(ComsesDigest.objects.get(doi=self.record["doi"]).id, digest_id)
        self.assertEqual(ComsesDigest.objects.count(), 1)

    def test_metadata_changes_update_existing_entry(self):
        self.run_command_with_records([self.record])
        digest = ComsesDigest.objects.get(doi=self.record["doi"])
        digest_id = digest.id
        updated_record = deepcopy(self.record)
        updated_record["metadata"].update(
            {
                "title": "Updated CoMSES Digest",
                "publication_date": "2025-02-20",
            }
        )
        updated_record["metadata"]["journal"] = {"volume": "2", "issue": "3"}
        updated_record["links"]["latest_html"] = "https://zenodo.org/records/7654321"

        self.run_command_with_records([updated_record])

        digest.refresh_from_db()
        self.assertEqual(digest.id, digest_id)
        self.assertEqual(digest.title, "Updated CoMSES Digest")
        self.assertEqual(digest.volume, 2)
        self.assertEqual(digest.issue_number, 3)
        self.assertEqual(digest.publication_date, date(2025, 2, 20))
        self.assertEqual(digest.url, "https://zenodo.org/records/7654321")

    def test_entries_missing_from_response_are_preserved(self):
        existing = self.create_existing_digest()

        self.run_command_with_records([self.record])

        self.assertTrue(ComsesDigest.objects.filter(id=existing.id).exists())

    def test_fetch_failure_leaves_database_unchanged(self):
        self.create_existing_digest()
        before = list(ComsesDigest.objects.order_by("pk").values())

        with patch(
            "home.management.commands.update_digest_archive.iter_zenodo_records",
            side_effect=requests.RequestException("unavailable"),
        ):
            with self.assertRaisesRegex(CommandError, "Failed to fetch"):
                call_command("update_digest_archive")

        self.assertEqual(list(ComsesDigest.objects.order_by("pk").values()), before)

    def test_invalid_metadata_leaves_database_unchanged(self):
        existing = self.create_existing_digest(doi=self.record["doi"])
        invalid_record = deepcopy(self.record)
        invalid_record["metadata"]["publication_date"] = "not-a-date"

        with self.assertRaisesRegex(CommandError, "Invalid metadata"):
            self.run_command_with_records([self.record, invalid_record])

        existing.refresh_from_db()
        self.assertEqual(existing.title, "Existing digest")
        self.assertEqual(ComsesDigest.objects.count(), 1)

    def test_write_failure_rolls_back_entire_batch(self):
        existing = self.create_existing_digest(doi=self.record["doi"])
        second_record = deepcopy(self.record)
        second_record["doi"] = "10.5281/zenodo.7654321"
        original_update_or_create = ComsesDigest.objects.update_or_create
        calls = 0

        def fail_second_write(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("write failed")
            return original_update_or_create(*args, **kwargs)

        with patch.object(ComsesDigest.objects, "update_or_create", side_effect=fail_second_write):
            with self.assertRaisesRegex(CommandError, "Failed to import"):
                self.run_command_with_records([self.record, second_record])

        existing.refresh_from_db()
        self.assertEqual(existing.title, "Existing digest")
        self.assertEqual(ComsesDigest.objects.count(), 1)
