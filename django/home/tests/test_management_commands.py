import json
from copy import deepcopy
from datetime import date
from unittest.mock import call, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import TestCase

from home.management.commands.update_digest_archive import ZENODO_COMMUNITY_API_URL, parse_zenodo_record
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

    def make_response(self, records, next_url=None, status_code=200):
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(
            {"hits": {"hits": records}, "links": {"next": next_url} if next_url else {}}
        ).encode("utf-8")
        return response

    @patch("home.management.commands.update_digest_archive.requests.Session.get")
    def test_imports_multiple_pages(self, get):
        second_record = deepcopy(self.record)
        second_record["doi"] = "10.5281/zenodo.7654321"
        second_record["metadata"]["journal"]["issue"] = "2"
        second_record["links"]["latest_html"] = "https://zenodo.org/records/7654321"
        next_url = f"{ZENODO_COMMUNITY_API_URL}?page=2&size=25&sort=publication-desc"
        get.side_effect = [
            self.make_response([self.record], next_url=next_url),
            self.make_response([second_record]),
        ]

        call_command("update_digest_archive")

        self.assertEqual(
            get.call_args_list,
            [
                call(f"{ZENODO_COMMUNITY_API_URL}?page=1&size=25&sort=publication-desc", timeout=10),
                call(next_url, timeout=10),
            ],
        )
        self.assertCountEqual(
            ComsesDigest.objects.values_list("doi", "issue_number"),
            [(self.record["doi"], 1), (second_record["doi"], 2)],
        )

    @patch("home.management.commands.update_digest_archive.requests.Session.get")
    def test_second_page_failure_leaves_database_unchanged(self, get):
        self.create_existing_digest(doi=self.record["doi"])
        self.create_existing_digest()
        before = list(ComsesDigest.objects.order_by("pk").values())
        new_record = deepcopy(self.record)
        new_record["doi"] = "10.5281/zenodo.7654321"
        next_url = f"{ZENODO_COMMUNITY_API_URL}?page=2&size=25&sort=publication-desc"
        get.side_effect = [
            self.make_response([self.record, new_record], next_url=next_url),
            self.make_response([], status_code=503),
        ]

        with self.assertRaisesRegex(CommandError, "Failed to fetch") as raised:
            call_command("update_digest_archive")

        self.assertIsInstance(raised.exception.__cause__, requests.HTTPError)
        self.assertEqual(
            get.call_args_list,
            [
                call(f"{ZENODO_COMMUNITY_API_URL}?page=1&size=25&sort=publication-desc", timeout=10),
                call(next_url, timeout=10),
            ],
        )
        self.assertEqual(list(ComsesDigest.objects.order_by("pk").values()), before)

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

        with self.assertRaisesRegex(CommandError, "Invalid metadata") as raised:
            self.run_command_with_records([self.record, invalid_record])

        self.assertIn(self.record["doi"], str(raised.exception))
        self.assertIn("not-a-date", str(raised.exception))
        existing.refresh_from_db()
        self.assertEqual(existing.title, "Existing digest")
        self.assertEqual(ComsesDigest.objects.count(), 1)

    def test_invalid_doi_has_a_specific_error(self):
        for doi in (None, "", "   ", 123):
            with self.subTest(doi=doi):
                record = deepcopy(self.record)
                record["doi"] = doi
                with self.assertRaisesRegex(CommandError, "DOI is required"):
                    parse_zenodo_record(record)
        record = deepcopy(self.record)
        del record["doi"]
        with self.assertRaisesRegex(CommandError, "DOI is required"):
            parse_zenodo_record(record)

    def test_missing_metadata_identifies_the_record_and_field(self):
        record = deepcopy(self.record)
        del record["metadata"]["journal"]["issue"]

        with self.assertRaises(CommandError) as raised:
            parse_zenodo_record(record)

        self.assertIn(record["doi"], str(raised.exception))
        self.assertIn("issue", str(raised.exception))
        self.assertIsInstance(raised.exception.__cause__, KeyError)

    @patch("home.management.commands.update_digest_archive.requests.Session.get")
    def test_malformed_response_leaves_database_unchanged(self, get):
        self.create_existing_digest()
        before = list(ComsesDigest.objects.order_by("pk").values())
        for content in (b"not json", b"{}"):
            with self.subTest(content=content):
                response = requests.Response()
                response.status_code = 200
                response._content = content
                get.return_value = response

                with self.assertRaisesRegex(CommandError, "Failed to fetch"):
                    call_command("update_digest_archive")

                self.assertEqual(list(ComsesDigest.objects.order_by("pk").values()), before)

    def test_unexpected_fetch_errors_propagate(self):
        with patch(
            "home.management.commands.update_digest_archive.requests.Session.get",
            side_effect=RuntimeError("unexpected bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                call_command("update_digest_archive")

    def test_unexpected_write_errors_propagate(self):
        with patch.object(ComsesDigest.objects, "update_or_create", side_effect=RuntimeError("unexpected bug")):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                self.run_command_with_records([self.record])

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
                raise DatabaseError("write failed")
            return original_update_or_create(*args, **kwargs)

        with patch.object(ComsesDigest.objects, "update_or_create", side_effect=fail_second_write):
            with self.assertRaisesRegex(CommandError, "Failed to import"):
                self.run_command_with_records([self.record, second_record])

        existing.refresh_from_db()
        self.assertEqual(existing.title, "Existing digest")
        self.assertEqual(ComsesDigest.objects.count(), 1)
