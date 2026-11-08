import io
import tarfile
import stat
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from core import fs
from library.fs import (
    ArchiveExtractor,
    FileCategories,
    Message,
    MessageLevels,
    ImportedCodebaseReleaseFsApi,
    extract_zip_without_top_dir,
)


class TarExtractionSecurityTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / "extracted"
        self.destination.mkdir()
        self.sentinel = self.root / "sentinel.txt"
        self.sentinel.write_bytes(b"private data")
        self.archive = self.root / "upload.tar"
        self.storage = Mock()
        self.extractor = ArchiveExtractor(self.storage)

    def write_archive(self, members):
        with tarfile.open(self.archive, "w") as archive:
            for member, content in members:
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

    def test_rejects_paths_outside_destination(self):
        for name in ("../sentinel.txt", "nested/../../sentinel.txt", str(self.sentinel)):
            with self.subTest(name=name):
                self.write_archive([(tarfile.TarInfo(name), b"overwritten")])
                with self.assertRaises(tarfile.FilterError):
                    self.extractor.extractall(self.destination, str(self.archive))
                self.assertEqual(self.sentinel.read_bytes(), b"private data")
                self.assertEqual(list(self.destination.iterdir()), [])

    def test_rejects_links_and_special_files(self):
        for member_type in (
            tarfile.SYMTYPE,
            tarfile.LNKTYPE,
            tarfile.FIFOTYPE,
            tarfile.CHRTYPE,
            tarfile.BLKTYPE,
        ):
            with self.subTest(member_type=member_type):
                member = tarfile.TarInfo("unsafe")
                member.type = member_type
                member.linkname = str(self.sentinel)
                self.write_archive([(member, b"")])
                with self.assertRaises(tarfile.FilterError):
                    self.extractor.extractall(self.destination, str(self.archive))
                self.assertEqual(list(self.destination.iterdir()), [])
                self.assertEqual(self.sentinel.read_bytes(), b"private data")

    def test_rejects_internal_links_too(self):
        for member_type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            with self.subTest(member_type=member_type):
                link = tarfile.TarInfo("alias.txt")
                link.type = member_type
                link.linkname = "safe.txt"
                self.write_archive([(tarfile.TarInfo("safe.txt"), b"safe"), (link, b"")])
                result = self.extractor.process(FileCategories.code, str(self.archive))
                self.assertEqual(result.level, MessageLevels.error)
                self.storage.log_save.assert_not_called()

    def test_link_then_write_cannot_escape(self):
        link = tarfile.TarInfo("outside")
        link.type = tarfile.SYMTYPE
        link.linkname = str(self.root)
        self.write_archive([(link, b""), (tarfile.TarInfo("outside/sentinel.txt"), b"overwritten")])
        with self.assertRaises(tarfile.FilterError):
            self.extractor.extractall(self.destination, str(self.archive))
        self.assertEqual(self.sentinel.read_bytes(), b"private data")

    def test_rejected_archive_imports_no_files_or_external_contents(self):
        link = tarfile.TarInfo("secret.txt")
        link.type = tarfile.SYMTYPE
        link.linkname = str(self.sentinel)
        for unsafe_member in (link, tarfile.TarInfo(str(self.sentinel))):
            with self.subTest(member_type=unsafe_member.type):
                self.write_archive([(tarfile.TarInfo("safe.txt"), b"safe"), (unsafe_member, b"")])
                result = self.extractor.process(FileCategories.code, str(self.archive))
                self.assertEqual(result.level, MessageLevels.error)
                self.storage.log_save.assert_not_called()
                self.assertEqual(self.sentinel.read_bytes(), b"private data")

    def test_regular_files_and_directories_are_imported(self):
        directory = tarfile.TarInfo("project/src")
        directory.type = tarfile.DIRTYPE
        self.write_archive(
            [
                (directory, b""),
                (tarfile.TarInfo("project/README.md"), b"readme"),
                (tarfile.TarInfo("project/src/model.py"), b"print('model')"),
            ]
        )
        imported = {}

        def save(name, content):
            imported[name] = content.read()
            return Message("saved")

        self.storage.log_save.side_effect = save
        result = self.extractor.process(FileCategories.code, str(self.archive))
        self.assertFalse(result.has_errors)
        self.assertEqual(
            imported,
            {
                "code/README.md": b"readme",
                "code/src/model.py": b"print('model')",
            },
        )


class ZipExtractionSecurityTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / "extracted"
        self.destination.mkdir()
        self.sentinel = self.root / "sentinel.txt"
        self.sentinel.write_bytes(b"private data")
        self.archive = self.root / "upload.zip"

    def write_archive(self, names):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name in names:
                archive.writestr(name, b"contents")

    def test_rejects_unsafe_paths_before_writing_any_files(self):
        for name in ("../sentinel.txt", "project/../../sentinel.txt", str(self.sentinel), "C:/escape", "..\\escape"):
            with self.subTest(name=name):
                self.write_archive(["project/safe.txt", name])
                with self.assertRaises(ValueError):
                    extract_zip_without_top_dir(self.archive, self.destination)
                self.assertEqual(self.sentinel.read_bytes(), b"private data")
                self.assertEqual(list(self.destination.iterdir()), [])

    def test_strips_only_a_shared_directory(self):
        for names, expected in (
            (["project/", "project/README", "project/src/model.py"], {"README", "src/model.py"}),
            (["README"], {"README"}),
            (["prefix-one", "prefix-two"], {"prefix-one", "prefix-two"}),
            (["a/file", "b/file"], {"a/file", "b/file"}),
            ([], set()),
        ):
            with self.subTest(names=names), TemporaryDirectory() as destination:
                self.write_archive(names)
                extract_zip_without_top_dir(self.archive, Path(destination))
                files = {p.relative_to(destination).as_posix() for p in Path(destination).rglob("*") if p.is_file()}
                self.assertEqual(files, expected)

    def test_rejects_links_and_special_files(self):
        for file_type in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFBLK):
            with self.subTest(file_type=file_type):
                member = zipfile.ZipInfo("project/unsafe")
                member.create_system = 3
                member.external_attr = (file_type | 0o777) << 16
                self.write_archive(["project/safe", member])
                with self.assertRaises(ValueError):
                    extract_zip_without_top_dir(self.archive, self.destination)
                self.assertEqual(list(self.destination.iterdir()), [])

    def test_rejects_existing_destination_symlink(self):
        (self.destination / "sentinel.txt").symlink_to(self.sentinel)
        self.write_archive(["project/sentinel.txt"])
        with self.assertRaises(ValueError):
            extract_zip_without_top_dir(self.archive, self.destination)
        self.assertEqual(self.sentinel.read_bytes(), b"private data")

    def test_invalid_archive_preserves_existing_sip(self):
        existing = self.destination / "existing.txt"
        existing.write_bytes(b"existing")
        api = Mock()
        storage = api.get_sip_storage.return_value
        storage.location = str(self.destination)
        self.write_archive(["project/safe", "../sentinel.txt"])
        with self.assertRaises(ValueError):
            ImportedCodebaseReleaseFsApi.extract_to_sip(api, self.archive)
        storage.clear.assert_not_called()
        self.assertEqual(existing.read_bytes(), b"existing")

    def test_corrupt_member_preserves_existing_sip(self):
        self.write_archive(["project/file"])
        data = self.archive.read_bytes().replace(b"contents", b"corrupt!")
        self.archive.write_bytes(data)
        api = Mock()
        api.get_sip_storage.return_value.location = str(self.destination)
        with self.assertRaises(zipfile.BadZipFile):
            ImportedCodebaseReleaseFsApi.extract_to_sip(api, self.archive)
        api.get_sip_storage.return_value.clear.assert_not_called()

    def test_valid_archive_replaces_sip_after_extraction(self):
        existing = self.destination / "existing.txt"
        existing.write_bytes(b"existing")
        self.write_archive(["project/README"])
        api = Mock()
        storage = api.get_sip_storage.return_value
        storage.location = str(self.destination)
        storage.clear.side_effect = existing.unlink
        ImportedCodebaseReleaseFsApi.extract_to_sip(api, self.archive)
        storage.clear.assert_called_once_with()
        self.assertFalse(existing.exists())
        self.assertEqual((self.destination / "README").read_bytes(), b"contents")


class RarExtractionSecurityTests(SimpleTestCase):
    def member(self, name="safe.txt", **overrides):
        member = Mock(filename=name, file_redir=None)
        member.is_symlink.return_value = False
        member.is_file.return_value = True
        member.is_dir.return_value = False
        for key, value in overrides.items():
            setattr(member, key, value)
        return member

    def test_rejects_unsafe_members_before_extraction(self):
        symlink = self.member()
        symlink.is_symlink.return_value = True
        special = self.member()
        special.is_file.return_value = False
        members = [symlink, special, self.member("../escape"), self.member("/absolute")]
        # RAR5 redirections include symlinks, junctions, hard links and file copies.
        members.extend(self.member(file_redir=(kind, 0, "target")) for kind in range(1, 6))
        for member in members:
            with self.subTest(member=member), TemporaryDirectory() as destination:
                with patch("core.fs.rarfile.RarFile") as rar:
                    archive = rar.return_value.__enter__.return_value
                    archive.infolist.return_value = [self.member(), member]
                    with self.assertRaises(ValueError):
                        fs.unrar("upload.rar", destination)
                    archive.extractall.assert_not_called()

    def test_regular_members_are_passed_to_extractor(self):
        with TemporaryDirectory() as destination, patch("core.fs.rarfile.RarFile") as rar:
            archive = rar.return_value.__enter__.return_value
            directory = self.member("project/")
            directory.is_file.return_value = False
            directory.is_dir.return_value = True
            members = [directory, self.member("project/file")]
            archive.infolist.return_value = members
            fs.unrar("upload.rar", destination)
            archive.extractall.assert_called_once_with(destination, members=members)

    def test_upload_rejects_rar_without_importing_contents(self):
        # Exercise the existing RAR branch regardless of the OS MIME database.
        with (
            patch("core.fs.rarfile.RarFile") as rar,
            patch("library.fs.mimetypes.guess_type", return_value=("application/rar", None)),
        ):
            archive = rar.return_value.__enter__.return_value
            archive.infolist.return_value = [self.member(file_redir=(1, 0, "/secret"))]
            storage = Mock()
            with self.assertLogs("library.fs", level="ERROR"):
                result = ArchiveExtractor(storage).process(FileCategories.code, "upload.rar")
            self.assertEqual(result.level, MessageLevels.error)
            storage.log_save.assert_not_called()
            archive.extractall.assert_not_called()
