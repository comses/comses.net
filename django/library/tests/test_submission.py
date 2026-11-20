"""Exercise submission HTTP endpoints, storage, manifests and archives together."""

import hashlib
import io
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from core.tests.base import UserFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from django.core.management import call_command
from library.fs import FileCategories
from library.models import CodebaseRelease, ImportedReleaseSyncState
from library.tests.base import CodebaseFactory, ReleaseSetup


def bundle(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    return SimpleUploadedFile("model.zip", output.getvalue(), "application/zip")


class SubmissionIntegrationTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        settings = override_settings(LIBRARY_ROOT=self.temporary.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = UserFactory().create()
        self.codebase = CodebaseFactory(self.user).create()
        self.release = ReleaseSetup.setUpPublishableDraftRelease(
            self.codebase, with_files=False
        )
        self.client = APIClient(HTTP_ACCEPT="application/json")
        self.client.force_authenticate(self.user)
        self.url = self.release.get_absolute_url()
        self.files_url = self.url + "files/package/"
        self.category_url = self.url + "files/sip/code/update_category/"
        self.root = self.release.get_fs_api().sip_contents_dir

    def upload(self, files):
        response = self.client.post(
            self.files_url, {"file": bundle(files)}, format="multipart"
        )
        self.assertEqual(response.status_code, 202, response.content)

    def categorize(self, path, category):
        response = self.client.post(
            self.category_url, {"path": path, "category": category}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

    @patch("library.tasks.sync_release_submitter_to_discourse")
    def test_bundle_categorization_publication_and_download(self, notify):
        files = {
            "simulation/main.py": b"print('model')",
            "guide.txt": b"Instructions",
            "inputs/values.csv": b"1,2",
        }
        self.upload(files)
        response = self.client.post(
            self.files_url,
            {"file": SimpleUploadedFile("__init__.py", b"")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 202, response.content)
        files["__init__.py"] = b""
        response = self.client.post(
            self.url + "publish/", {"version_number": "1.0.0"}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.categorize("guide.txt", "docs")
        self.categorize("inputs/values.csv", "data")
        self.release.refresh_from_db()
        self.assertEqual(self.release.category_manifest["guide.txt"], "docs")
        preview = self.client.get(self.url + "download_preview/")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("simulation", str(preview.data))
        response = self.client.post(
            self.url + "publish/", {"version_number": "1.0.0"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        download = self.client.get(self.url + "download/")
        self.assertEqual(download.status_code, 200, download.content)
        self.release.refresh_from_db()
        archive_path = self.release.get_fs_api().archivepath
        self.assertIn(
            str(archive_path.relative_to(self.temporary.name)),
            download["X-Accel-Redirect"],
        )
        with zipfile.ZipFile(archive_path) as archive:
            for name, contents in files.items():
                self.assertEqual(archive.read(name), contents)
            self.assertNotIn("code/simulation/main.py", archive.namelist())

    def test_add_remove_and_reject_partial_or_unsafe_uploads(self):
        self.upload(
            {"main.py": b"code", "README.md": b"docs", "inputs/data.csv": b"data"}
        )
        response = self.client.post(
            self.files_url,
            {"file": SimpleUploadedFile("extra.py", b"extra")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 202, response.content)
        self.categorize("inputs/data.csv", "data")
        response = self.client.delete(self.files_url + "inputs/data.csv/")
        self.assertEqual(response.status_code, 202, response.content)
        self.assertFalse((self.root / "inputs").exists())
        self.upload({"inputs": b"replacement file"})
        for bad_files in [
            {"new.py": b"new", "main.py": b"collision"},
            {"new.py": b"new", "../escape.py": b"unsafe"},
        ]:
            response = self.client.post(
                self.files_url, {"file": bundle(bad_files)}, format="multipart"
            )
            self.assertEqual(response.status_code, 400, response.content)
            self.assertFalse((self.root / "new.py").exists())
            self.assertEqual((self.root / "main.py").read_bytes(), b"code")
        self.release.refresh_from_db()
        self.assertNotIn("inputs/data.csv", self.release.category_manifest)
        self.assertNotIn("new.py", self.release.category_manifest)
        self.assertEqual(self.release.category_manifest["extra.py"], "code")

    def test_archive_limits_preserve_existing_package_and_manifest(self):
        self.upload({"main.py": b"original", "README.md": b"docs"})
        self.release.refresh_from_db()
        manifest = dict(self.release.category_manifest)
        files = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for kind in ("zip", "tar", "tar.gz"):
            output = io.BytesIO()
            if kind == "zip":
                with zipfile.ZipFile(output, "w") as archive:
                    archive.writestr("new.py", b"too large")
            else:
                with tarfile.open(fileobj=output, mode="w:gz" if kind == "tar.gz" else "w") as archive:
                    member = tarfile.TarInfo("new.py")
                    member.size = 9
                    archive.addfile(member, io.BytesIO(b"too large"))
            with self.subTest(kind=kind), override_settings(ARCHIVE_MAX_FILE_BYTES=2):
                response = self.client.post(
                    self.files_url,
                    {"file": SimpleUploadedFile(f"upload.{kind}", output.getvalue())},
                    format="multipart",
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertNotIn(str(self.root.parent), str(response.data))
                self.release.refresh_from_db()
                self.assertEqual(self.release.category_manifest, manifest)
                self.assertEqual(
                    {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()},
                    files,
                )

    def test_upload_and_delete_do_not_copy_unchanged_files(self):
        self.upload({"inputs/large.dat": b"x" * 1024 * 1024, "README.md": b"docs"})
        existing = self.root / "inputs/large.dat"
        original_inode = existing.stat().st_ino

        self.upload({"extra.py": b"code"})
        self.assertEqual(existing.stat().st_ino, original_inode)
        self.assertEqual(existing.stat().st_nlink, 1)
        response = self.client.delete(self.files_url + "extra.py/")
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(existing.stat().st_ino, original_inode)
        self.assertEqual(existing.stat().st_nlink, 1)
        self.assertEqual(existing.read_bytes(), b"x" * 1024 * 1024)

    def test_failed_edits_restore_files_and_manifest(self):
        self.upload({"main.py": b"code", "README.md": b"docs", "LICENSE": b"original license"})
        self.release.refresh_from_db()
        manifest = dict(self.release.category_manifest)
        files = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        api = self.release.get_fs_api()
        edits = {
            "replace metadata": lambda: api.add(content=bundle({"LICENSE": b"replacement", "new.py": b"new"})),
            "delete file": lambda: api.delete(None, Path("main.py")),
            "clear category": lambda: api.clear_category(FileCategories.docs),
        }
        for name, edit in edits.items():
            with self.subTest(edit=name):
                with patch("library.fs.CategoryManifestManager.update", side_effect=RuntimeError("database failure")):
                    with self.assertRaisesMessage(RuntimeError, "database failure"):
                        edit()
                self.release.refresh_from_db()
                self.assertEqual(self.release.category_manifest, manifest)
                self.assertEqual(
                    {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()},
                    files,
                )
                self.assertTrue(all(p.stat().st_nlink == 1 for p in self.root.rglob("*") if p.is_file()))

    def test_rejected_upload_does_not_modify_existing_metadata(self):
        self.upload({"main.py": b"original code", "LICENSE": b"original license"})
        response = self.client.post(
            self.files_url,
            {"file": bundle({"LICENSE": b"replacement", "main.py": b"collision"})},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual((self.root / "LICENSE").read_bytes(), b"original license")
        self.assertEqual((self.root / "main.py").read_bytes(), b"original code")

    def test_failed_release_copy_preserves_source_and_destination(self):
        self.upload({"LICENSE": b"destination license"})
        source = ReleaseSetup.setUpPublishableDraftRelease(
            CodebaseFactory(self.user).create(), with_files=False
        )
        source_api = source.get_fs_api()
        source_api.add(content=bundle({"LICENSE": b"source license", "main.py": b"source code"}))
        self.release.refresh_from_db()
        manifest = dict(self.release.category_manifest)
        with patch("library.fs.CategoryManifestManager.update", side_effect=RuntimeError("database failure")):
            with self.assertRaisesMessage(RuntimeError, "database failure"):
                self.release.get_fs_api().copy_originals(source)
        self.release.refresh_from_db()
        self.assertEqual(self.release.category_manifest, manifest)
        self.assertEqual((self.root / "LICENSE").read_bytes(), b"destination license")
        self.assertFalse((self.root / "main.py").exists())
        self.assertEqual((source_api.sip_contents_dir / "LICENSE").read_bytes(), b"source license")
        self.assertEqual((source_api.sip_contents_dir / "main.py").read_bytes(), b"source code")

    def test_metadata_save_preserves_new_uploads_and_category_edits(self):
        self.upload({"main.py": b"code", "guide.txt": b"docs"})
        for rebuild_metadata in [False, True]:
            stale_release = CodebaseRelease.objects.get(pk=self.release.pk)
            name = f"extra-{rebuild_metadata}.py"
            self.upload({name: b"extra"})
            self.categorize(name, "docs")
            stale_release.summary = "Updated release summary"
            stale_release.save(rebuild_metadata=rebuild_metadata)
            self.release.refresh_from_db()
            self.assertEqual(self.release.category_manifest[name], "docs")
            self.assertEqual(self.release.summary, "Updated release summary")
            response = self.client.delete(self.files_url + name + "/")
            self.assertEqual(response.status_code, 202, response.content)

    def test_deferred_metadata_save_updates_export_snapshot(self):
        release = CodebaseRelease.objects.only("id", "summary").get(pk=self.release.pk)
        self.codebase.title = "Updated model title"
        self.codebase.save(rebuild_release_metadata=False)
        release.summary = "Updated release summary"
        release.save()
        self.release.refresh_from_db()
        self.assertEqual(self.release.codemeta_snapshot["name"], "Updated model title")

    def test_reserved_metadata_paths_cannot_be_directories(self):
        for name in ["LICENSE", "CITATION.cff", "codemeta.json"]:
            (self.root / name).unlink(missing_ok=True)
            response = self.client.post(
                self.files_url,
                {"file": bundle({f"{name}/nested.txt": b"blocked"})},
                format="multipart",
            )
            self.assertEqual(response.status_code, 400, response.content)
            self.assertFalse((self.root / name).exists())

    def test_permissions_and_locked_packages(self):
        self.upload({"main.py": b"code", "README.md": b"docs"})
        other = UserFactory().create(username="unrelated-submitter")
        for user, status in [
            (other, CodebaseRelease.Status.DRAFT),
            (self.user, CodebaseRelease.Status.PUBLISHED),
            (self.user, CodebaseRelease.Status.REVIEW_COMPLETE),
        ]:
            self.client.force_authenticate(user)
            CodebaseRelease.objects.filter(pk=self.release.pk).update(status=status)
            responses = [
                self.client.post(
                    self.files_url,
                    {"file": SimpleUploadedFile("extra.py", b"extra")},
                    format="multipart",
                ),
                self.client.delete(self.files_url + "main.py/"),
                self.client.post(
                    self.category_url,
                    {"path": "main.py", "category": "data"},
                    format="json",
                ),
            ]
            for response in responses:
                self.assertIn(response.status_code, [403, 404], response.content)
        self.release.refresh_from_db()
        self.assertEqual(self.release.category_manifest["main.py"], "code")
        self.assertTrue((self.root / "main.py").exists())
        self.assertFalse((self.root / "extra.py").exists())

    def test_backfill_preserves_legacy_files_metadata_and_existing_assignments(self):
        for name in [
            "code/src/main.py",
            "docs/guide.txt",
            "data/inputs.csv",
            "results/run/output.csv",
            "CITATION.cff",
        ]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        fs_api = self.release.get_fs_api()
        fs_api.build_archive()
        CodebaseRelease.objects.filter(pk=self.release.pk).update(
            status=CodebaseRelease.Status.PUBLISHED,
            doi="10.1234/example",
            category_manifest=None,
        )
        before = CodebaseRelease.objects.values().get(pk=self.release.pk)
        hashes = {
            path.relative_to(fs_api.rootdir): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in fs_api.rootdir.rglob("*")
            if path.is_file()
        }
        call_command("backfill_category_manifests", stdout=io.StringIO())
        self.release.refresh_from_db()
        self.assertEqual(
            self.release.category_manifest,
            {
                "code/src/main.py": "code",
                "docs/guide.txt": "docs",
                "data/inputs.csv": "data",
                "results/run/output.csv": "results",
                "CITATION.cff": "metadata",
            },
        )
        after = CodebaseRelease.objects.values().get(pk=self.release.pk)
        before.pop("category_manifest")
        after.pop("category_manifest")
        self.assertEqual(before, after)
        self.assertEqual(
            hashes,
            {
                path.relative_to(fs_api.rootdir): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in fs_api.rootdir.rglob("*")
                if path.is_file()
            },
        )
        first = dict(self.release.category_manifest)
        call_command("backfill_category_manifests", stdout=io.StringIO())
        self.release.refresh_from_db()
        self.assertEqual(first, self.release.category_manifest)

    def test_github_manifest_backfill_and_import(self):
        state = ImportedReleaseSyncState.objects.create(
            github_release_id="123",
            tag_name="v1.0.0",
            category_manifest={"custom.txt": "docs"},
        )
        CodebaseRelease.objects.filter(pk=self.release.pk).update(
            imported_release_sync_state=state, category_manifest=None
        )
        call_command("backfill_category_manifests", stdout=io.StringIO())
        self.release.refresh_from_db()
        self.assertEqual(self.release.category_manifest, {"custom.txt": "docs"})
        self.categorize("custom.txt", "data")
        call_command("backfill_category_manifests", stdout=io.StringIO())
        self.release.refresh_from_db()
        self.assertEqual(self.release.category_manifest, {"custom.txt": "data"})
        archive = Path(self.temporary.name) / "github.zip"
        archive.write_bytes(
            bundle({"repo-tag/main.py": b"code", "repo-tag/README.md": b"docs"}).read()
        )
        fs_api = self.release.get_fs_api()
        with patch.object(fs_api, "download_archive", return_value=archive):
            fs_api.import_release_package("unused")
        self.release.refresh_from_db()
        self.assertEqual(
            self.release.category_manifest, {"main.py": "code", "README.md": "docs"}
        )
        self.assertEqual((self.root / "main.py").read_bytes(), b"code")
        response = self.client.post(
            self.files_url,
            {"file": SimpleUploadedFile("extra.py", b"extra")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.content)
