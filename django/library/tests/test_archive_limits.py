import io
import tarfile
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from core import fs
from library.fs import ArchiveExtractor, FileCategories, ImportedCodebaseReleaseFsApi


class ArchiveBudgetTests(SimpleTestCase):
    def test_checks_actual_output_before_writing_over_limit(self):
        with override_settings(ARCHIVE_MAX_FILE_BYTES=3):
            budget = fs.ArchiveBudget()
            destination = io.BytesIO()
            with self.assertRaises(fs.ArchiveLimitError):
                budget.copy(io.BytesIO(b"four"), destination)
            self.assertEqual(destination.getvalue(), b"")

    def test_total_actual_output_is_shared_across_files(self):
        with override_settings(ARCHIVE_MAX_TOTAL_BYTES=3):
            budget = fs.ArchiveBudget()
            budget.copy(io.BytesIO(b"one"), io.BytesIO())
            destination = io.BytesIO()
            with self.assertRaises(fs.ArchiveLimitError):
                budget.copy(io.BytesIO(b"x"), destination)
            self.assertEqual(destination.getvalue(), b"")

    def test_checks_deadline_after_a_slow_read(self):
        with override_settings(ARCHIVE_MAX_SECONDS=45), patch("core.fs.time.monotonic", side_effect=[0, 0, 46]):
            budget = fs.ArchiveBudget()
            destination = io.BytesIO()
            with self.assertRaises(fs.ArchiveLimitError):
                budget.copy(io.BytesIO(b"data"), destination)
            self.assertEqual(destination.getvalue(), b"")

    def test_rejects_disabled_limits(self):
        with override_settings(ARCHIVE_MAX_MEMBERS=0), self.assertRaises(fs.ArchiveLimitError):
            fs.ArchiveBudget()


class ArchiveExtractionLimitTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def create_archive(self, kind, entries):
        path = self.root / f"upload.{kind}"
        if kind == "zip":
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries:
                    archive.writestr(name, data)
        else:
            with tarfile.open(path, "w") as archive:
                for name, data in entries:
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
        return path

    def test_upload_limits_reject_without_importing_any_contents(self):
        cases = (
            ({"ARCHIVE_MAX_INPUT_BYTES": 1}, [("safe", b"abc")]),
            ({"ARCHIVE_MAX_FILE_BYTES": 2}, [("safe", b"abc")]),
            ({"ARCHIVE_MAX_TOTAL_BYTES": 3}, [("a", b"ab"), ("b", b"cd")]),
            ({"ARCHIVE_MAX_MEMBERS": 1}, [("a", b""), ("b", b"")]),
            ({"ARCHIVE_MAX_PATH_DEPTH": 2}, [("a/b/c", b"abc")]),
        )
        for kind in ("zip", "tar"):
            for limits, entries in cases:
                with self.subTest(kind=kind, limits=limits), override_settings(**limits):
                    archive = self.create_archive(kind, entries)
                    storage = Mock()
                    result = ArchiveExtractor(storage).process(FileCategories.code, str(archive))
                    self.assertTrue(result.has_errors)
                    storage.log_save.assert_not_called()

    def test_exact_size_and_count_limits_are_allowed(self):
        for kind in ("zip", "tar"):
            with self.subTest(kind=kind), override_settings(
                ARCHIVE_MAX_FILE_BYTES=3,
                ARCHIVE_MAX_TOTAL_BYTES=3,
                ARCHIVE_MAX_MEMBERS=1,
                ARCHIVE_MAX_PATH_DEPTH=1,
            ):
                archive = self.create_archive(kind, [("safe", b"abc")])
                destination = self.root / kind
                destination.mkdir()
                ArchiveExtractor(Mock()).extractall(destination, str(archive))
                self.assertEqual((destination / "safe").read_bytes(), b"abc")

    def test_imported_zip_limit_preserves_sip(self):
        archive = self.create_archive("zip", [("project/safe", b"abc")])
        api = Mock()
        with override_settings(ARCHIVE_MAX_FILE_BYTES=2), self.assertRaises(fs.ArchiveLimitError):
            ImportedCodebaseReleaseFsApi.extract_to_sip(api, archive)
        api.get_sip_storage.return_value.clear.assert_not_called()

    def test_empty_archive_cannot_bypass_deadline(self):
        for kind in ("zip", "tar"):
            with self.subTest(kind=kind):
                archive = self.create_archive(kind, [])
                with patch("core.fs.time.monotonic", side_effect=[0, 0, 46]):
                    with self.assertRaises(fs.ArchiveLimitError):
                        ArchiveExtractor(Mock()).extractall(self.root / "output", str(archive))

    def test_tar_preserves_executable_mode_without_special_bits(self):
        archive_path = self.root / "executable.tar"
        with tarfile.open(archive_path, "w") as archive:
            member = tarfile.TarInfo("script")
            member.mode = 0o6755
            member.size = 4
            archive.addfile(member, io.BytesIO(b"code"))
        destination = self.root / "output"
        ArchiveExtractor(Mock()).extractall(destination, str(archive_path))
        self.assertEqual((destination / "script").stat().st_mode & 0o7777, 0o755)

    def test_rar_declared_size_is_checked_before_decompression(self):
        archive_path = self.root / "upload.rar"
        archive_path.write_bytes(b"mock RAR")
        with override_settings(ARCHIVE_MAX_FILE_BYTES=2), patch("core.fs.rarfile.RarFile") as rar:
            archive = rar.return_value.__enter__.return_value
            archive.infolist.return_value = [Mock(filename="safe", file_size=3)]
            with self.assertRaises(fs.ArchiveLimitError):
                fs.unrar(archive_path, self.root / "destination")
            archive.open.assert_not_called()


class ArchiveDownloadTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.api = Mock()
        self.api.get_originals_storage.return_value.location = str(self.root)
        self.api.imported_release_sync_state.tag_name = "../../unsafe-tag"
        self.existing = self.root / "release.zip"
        self.existing.write_bytes(b"previous archive")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("project/README", b"safe")
        self.payload = buffer.getvalue()
        self.response = Mock(headers={})
        self.response.iter_content.return_value = iter([self.payload])
        self.request_patch = patch("library.fs.requests.get")
        self.get = self.request_patch.start()
        self.addCleanup(self.request_patch.stop)
        self.get.return_value.__enter__.return_value = self.response

    def download(self):
        return ImportedCodebaseReleaseFsApi.download_archive(self.api, "https://example.invalid/archive", "token")

    def assert_preserved(self):
        self.assertEqual(self.existing.read_bytes(), b"previous archive")
        self.assertEqual(list(self.root.iterdir()), [self.existing])

    def test_remote_names_never_determine_local_path(self):
        for disposition in (None, 'attachment; filename="../../outside.zip"', "attachment; filename=/tmp/outside.zip"):
            with self.subTest(disposition=disposition):
                self.response.headers = {} if disposition is None else {"content-disposition": disposition}
                self.response.iter_content.return_value = iter([self.payload])
                self.assertEqual(self.download(), self.existing)
                self.assertEqual(self.existing.read_bytes(), self.payload)
                self.assertEqual(list(self.root.iterdir()), [self.existing])
        self.assertEqual(self.get.call_args.kwargs["timeout"], (10, 15))

    def test_oversized_content_length_rejected_without_reading_body(self):
        self.response.headers = {"Content-Length": "101"}
        with override_settings(ARCHIVE_MAX_INPUT_BYTES=100), self.assertRaises(fs.ArchiveLimitError):
            self.download()
        self.response.iter_content.assert_not_called()
        self.assert_preserved()

    def test_stream_limit_does_not_trust_content_length(self):
        for headers in ({}, {"Content-Length": "1"}):
            with self.subTest(headers=headers):
                self.response.headers = headers
                self.response.iter_content.return_value = iter([b"123", b"456"])
                with override_settings(ARCHIVE_MAX_INPUT_BYTES=5), self.assertRaises(fs.ArchiveLimitError):
                    self.download()
                self.assert_preserved()

    def test_failed_stream_preserves_existing_archive_and_closes_response(self):
        def interrupted():
            yield b"partial"
            raise requests.Timeout("read timed out")

        self.response.iter_content.return_value = interrupted()
        with self.assertRaises(requests.Timeout):
            self.download()
        self.assert_preserved()
        self.get.return_value.__exit__.assert_called_once()

    def test_invalid_zip_preserves_existing_archive(self):
        self.response.iter_content.return_value = iter([b"not a zip"])
        with self.assertRaises(ValueError):
            self.download()
        self.assert_preserved()

    def test_deadline_preserves_existing_archive(self):
        with patch("core.fs.time.monotonic", side_effect=[0, 46]), self.assertRaises(fs.ArchiveLimitError):
            self.download()
        self.assert_preserved()

    def test_deadline_after_zip_check_preserves_existing_archive(self):
        with patch("core.fs.time.monotonic", side_effect=[0, 0, 0, 46]), self.assertRaises(fs.ArchiveLimitError):
            self.download()
        self.assert_preserved()

    def test_exact_input_size_limit_is_allowed(self):
        with override_settings(ARCHIVE_MAX_INPUT_BYTES=len(self.payload)):
            self.assertEqual(self.download().read_bytes(), self.payload)

    def test_http_error_preserves_existing_archive(self):
        self.response.raise_for_status.side_effect = requests.HTTPError("download failed")
        with self.assertRaises(requests.HTTPError):
            self.download()
        self.response.iter_content.assert_not_called()
        self.assert_preserved()

    def test_existing_symlink_is_replaced_without_overwriting_target(self):
        with TemporaryDirectory() as outside:
            sentinel = Path(outside) / "sentinel"
            sentinel.write_bytes(b"preserve")
            self.existing.unlink()
            self.existing.symlink_to(sentinel)
            self.download()
            self.assertFalse(self.existing.is_symlink())
            self.assertEqual(self.existing.read_bytes(), self.payload)
            self.assertEqual(sentinel.read_bytes(), b"preserve")
