import filecmp
import json
import logging
import mimetypes
import os
import re
import shutil
import tarfile
import zipfile
from enum import Enum
from functools import total_ordering
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import bagit
import requests
import yaml
from core import fs
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from git import Actor, InvalidGitRepositoryError, Repo
from packaging.version import Version
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

"""
FIXME: consider refactoring to use pathlib.Path throughout this module instead of string paths
"""


class StagingDirectories(Enum):
    # Directory containing original files uploaded (such as zip files)
    originals = 1
    # Directory containing submission information package files
    sip = 2
    # Directory containing archive information package files
    aip = 3


class FileCategories(Enum):
    code = 1
    data = 2
    docs = 3
    media = 4
    originals = 5
    results = 6
    metadata = 7


@total_ordering
class MessageLevels(Enum):
    debug = 0
    info = 1
    warning = 2
    error = 3
    critical = 4

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def downgrade(self, minimum=0):
        return MessageLevels(max(self.value - 1, minimum))


mimetypes.add_type("text/x-rst", ".rst")
mimetypes.add_type("text/x-netlogo", ".nls")
mimetypes.add_type("text/x-netlogo", ".nlogo")
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/x-r-source", ".r")

ACCEPT_ALL_REGEX = re.compile(r".*")

MIMETYPE_MATCHER = {
    FileCategories.code: ACCEPT_ALL_REGEX,
    FileCategories.data: ACCEPT_ALL_REGEX,
    FileCategories.docs: re.compile(
        r"text/markdown|application/pdf|text/plain|text/x-rtf|application/vnd.oasis.opendocument.text"
    ),
    FileCategories.media: re.compile(r"image/.*|video/.*"),
    FileCategories.originals: ACCEPT_ALL_REGEX,
    FileCategories.results: ACCEPT_ALL_REGEX,
}


def get_category(name) -> FileCategories:
    category_name = Path(name).parts[0]
    try:
        return FileCategories[category_name]
    except KeyError:
        raise ValidationError(
            "Target folder name {} invalid. Must be one of {}".format(
                category_name, list(d.name for d in FileCategories)
            )
        )


def get_mimetype_matcher(name):
    category = get_category(name)
    return MIMETYPE_MATCHER[category]


def files_in_dir(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            relpath = os.path.join(dirpath, filename)
            fullpath = os.path.join(path, relpath)
            if os.path.isfile(fullpath):
                yield relpath


class MessageGroup:
    def __init__(self, msgs=None):
        self.msgs = []
        self.level = MessageLevels.debug

        if msgs is not None:
            for msg in msgs:
                self.append(msg)

    def __bool__(self):
        return len(self.msgs) > 0

    def __repr__(self):
        return f"<MessageGroup {repr(self.msgs)}>"

    def append(self, msg: Optional):
        if msg is not None and msg:
            if isinstance(msg, MessageGroup):
                self.msgs += msg.msgs
            else:
                self.msgs.append(msg)
            logger.debug("msg: %s", msg)
            self.level = max(self.level, msg.level)

    def downgrade(self):
        self.level = self.level.downgrade()
        for msg in self.msgs:
            msg.level = msg.level.downgrade()

    @property
    def has_errors(self):
        return self.level >= MessageLevels.error

    def serialize(self):
        """Return a list of message along with message level"""
        return [msg.serialize() for msg in self.msgs], self.level


class Message:
    def __init__(self, msg, level: MessageLevels = MessageLevels.info):
        self.level = level
        self.msg = msg

    def __repr__(self):
        return repr(self.serialize())

    def serialize(self):
        return {"level": self.level.name, "msg": self.msg}

    @property
    def has_errors(self):
        return self.level >= MessageLevels.error


def create_fs_message(detail, stage: StagingDirectories, level: MessageLevels):
    return Message({"detail": str(detail), "stage": stage.name}, level=level)


class CodebaseReleaseStorage(FileSystemStorage):
    """
    storage abstraction for CodebaseRelease files
    """

    stage = None

    def __init__(
        self,
        mimetype_mismatch_message_level,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
    ):
        super().__init__(
            location=location,
            base_url=base_url,
            file_permissions_mode=file_permissions_mode,
            directory_permissions_mode=directory_permissions_mode,
        )
        self.mimetype_mismatch_message_level = mimetype_mismatch_message_level

    def validate_system_file(self, name, content) -> Optional[Message]:
        # FIXME: do we expect validate_file to be run on absolute paths?
        if fs.has_system_files(name):
            return self.error(f"Ignored system file '{name}'")
        return None

    def validate_mimetype(self, name):
        mimetype_matcher = get_mimetype_matcher(name)
        mimetype = mimetypes.guess_type(name)[0]
        mimetype = mimetype if mimetype else "*/*"
        if not mimetype_matcher.match(mimetype):
            return create_fs_message(
                f"Ignored file '{name}': invalid filetype {mimetype}",
                self.stage,
                self.mimetype_mismatch_message_level,
            )
        return None

    def validate_file(self, name, content):
        msgs = MessageGroup()
        msgs.append(self.validate_system_file(name, content))
        msgs.append(self.validate_mimetype(name))
        return msgs

    def validate(self):
        """Construct an audit report of a releases files"""
        msgs = MessageGroup()
        for filename in self.list():
            with self.open(filename) as content:
                msgs.append(self.validate_file(filename, content))
        return msgs

    def list(self, category: Optional[FileCategories] = None, absolute=False):
        path = Path(self.location)
        if category is not None:
            path = path.joinpath(category.name)
        for p in path.rglob("*"):
            if p.is_file():
                if absolute:
                    yield p
                else:
                    yield p.relative_to(path)

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            raise ValueError('Storage filename "%s" already taken' % name)
        return name

    def info(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.info)

    def warning(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.warning)

    def error(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.error)

    def critical(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.critical)

    def log_save(self, name, content):
        if name is None:
            name = content.name
        msgs = self.validate_file(name, content)
        if msgs.has_errors:
            return msgs

        try:
            self.save(name, content)
        except IOError as e:
            msgs.append(self.error(e))
        except ValueError as e:
            msgs.append(self.error(e))
        return msgs

    def clear_category(self, category: FileCategories):
        shutil.rmtree(os.path.join(self.location, category.name), ignore_errors=True)

    def clear(self):
        for p in Path(self.location).iterdir():
            if p.is_dir():
                shutil.rmtree(str(p), ignore_errors=True)

    def log_delete(self, name):
        try:
            self.delete(name)
        except IOError as e:
            return self.error(e)
        return None


class CodebaseReleaseOriginalStorage(CodebaseReleaseStorage):
    stage = StagingDirectories.originals

    def get_existing_archive_name(self, category: FileCategories):
        for p in self.list(category):
            if p.is_file() and fs.is_archive(p):
                return str(p)
        return None

    def is_archive_directory(self, category):
        for p in self.list(category, absolute=True):
            if p.is_file() and fs.is_archive(str(p)):
                return True
        return False

    def has_existing_archive(self, category):
        path = Path(self.location, category.name)
        os.makedirs(str(path), exist_ok=True)
        for subpath in path.glob("*"):
            if subpath.is_file() and fs.is_archive(str(subpath)):
                return True
        return False

    def validate_file(self, name, content):
        msgs = super().validate_file(name, content)
        category = get_category(name)
        if self.has_existing_archive(category):
            msgs.append(
                self.error(
                    "This file cannot be added because files have already been archived here."
                    " Please remove all files and try again."
                )
            )
        if os.listdir(os.path.join(self.location, category.name)) and fs.is_archive(
            name
        ):
            msgs.append(
                self.error(
                    "This archive cannot be added because files have already been archived here. "
                    "Please remove all files and try again."
                )
            )
        return msgs


class CodebaseReleaseSipStorage(CodebaseReleaseStorage):
    """Places files from the uploaded folder into the sip (submission information package)

    Archives from the uploads folder get expanded when placed in the sip folder"""

    stage = StagingDirectories.sip

    def make_bag(self, metadata):
        return fs.make_bag(self.location, metadata)


class CodebaseReleaseAipStorage(CodebaseReleaseStorage):
    """Places files from the sip folder into aip"""

    stage = StagingDirectories.aip

    def import_sip(self, sip_storage: CodebaseReleaseSipStorage):
        shutil.copytree(sip_storage.location, self.location)


class BaseCodebaseReleaseFsApi:
    """
    Base interface to maintain files associated with a codebase release
    """

    def __init__(
        self,
        codebase_release,
        system_file_presence_message_level=MessageLevels.error,
        mimetype_mismatch_message_level=MessageLevels.error,
    ):
        self.release = codebase_release
        self.uuid = str(codebase_release.codebase.uuid)
        self.identifier = codebase_release.codebase.identifier
        self.version_number = codebase_release.version_number
        self.release_id = codebase_release.id
        self.manifest = CategoryManifestManager(codebase_release)
        self.bagit_info = codebase_release.bagit_info
        self.mimetype_mismatch_message_level = mimetype_mismatch_message_level

    def logfilename(self):
        return self.rootdir.joinpath("audit.log")

    @property
    def lockfilename(self):
        return self.rootdir.joinpath("lock")

    @property
    def archivepath(self):
        return self.rootdir.joinpath("archive.zip")

    @property
    def review_archivepath(self):
        return self.rootdir.joinpath("review_archive.zip")

    @property
    def rootdir(self):
        return Path(
            settings.LIBRARY_ROOT, str(self.uuid), "releases", str(self.release_id)
        ).absolute()

    @property
    def aip_dir(self):
        return self.rootdir.joinpath("aip")

    @property
    def aip_contents_dir(self):
        return self.aip_dir.joinpath("data")

    @property
    def originals_dir(self):
        return self.rootdir.joinpath("originals")

    @property
    def sip_dir(self):
        return self.rootdir.joinpath("sip")

    @property
    def codemeta_contents(self) -> str:
        return self.release.codemeta_json_str

    @property
    def codemeta_path(self):
        return self.sip_contents_dir.joinpath("codemeta.json")

    @property
    def cff_contents(self) -> str:
        return self.release.cff_yaml_str

    @property
    def cff_path(self):
        return self.sip_contents_dir.joinpath("CITATION.cff")

    @property
    def license_path(self):
        return self.sip_contents_dir.joinpath("LICENSE")

    @property
    def sip_contents_dir(self):
        return self.sip_dir.joinpath("data")

    def get_originals_storage(self, originals_dir=None):
        if originals_dir is None:
            originals_dir = self.originals_dir
        return CodebaseReleaseOriginalStorage(
            mimetype_mismatch_message_level=self.mimetype_mismatch_message_level,
            location=str(originals_dir),
        )

    def get_sip_storage(self, mimetype_mismatch_message_level=None):
        if mimetype_mismatch_message_level is None:
            mimetype_mismatch_message_level = self.mimetype_mismatch_message_level
        return CodebaseReleaseSipStorage(
            mimetype_mismatch_message_level=mimetype_mismatch_message_level,
            location=str(self.sip_contents_dir),
        )

    def get_aip_storage(self):
        return CodebaseReleaseAipStorage(
            mimetype_mismatch_message_level=self.mimetype_mismatch_message_level,
            location=str(self.aip_contents_dir),
        )

    def get_stage_storage(self, stage: StagingDirectories):
        if stage == StagingDirectories.originals:
            return self.get_originals_storage()
        elif stage == StagingDirectories.sip:
            return self.get_sip_storage()
        elif stage == StagingDirectories.aip:
            return self.get_aip_storage()
        else:
            raise ValueError(f"StageDirectories values {stage} not valid")

    def get_sip_list_url(self, category: FileCategories):
        return reverse(
            "library:codebaserelease-sip-files-list",
            kwargs={
                "identifier": str(self.identifier),
                "version_number": self.version_number,
                "category": category.name,
            },
        )

    def get_originals_list_url(self, category: FileCategories):
        return reverse(
            "library:codebaserelease-original-files-list",
            kwargs={
                "identifier": str(self.identifier),
                "version_number": self.version_number,
                "category": category.name,
            },
        )

    def get_absolute_url(self, category: FileCategories, relpath: Path):
        return reverse(
            "library:codebaserelease-package-files-detail",
            kwargs={
                "identifier": str(self.identifier),
                "version_number": self.version_number,
                "relpath": str(relpath),
            },
        )

    def _create_msg_group(self):
        return MessageGroup()

    def validate_bagit(self, sip_bag=None):
        bag = sip_bag or self.get_or_create_sip_bag()
        try:
            bag.validate()
        except bagit.BagValidationError as e:
            logger.exception(e)

        for path, fixity in bag.entries.items():
            logger.info("path %s with md5 %s", path, fixity)

    @classmethod
    def initialize(
        cls,
        codebase_release,
        system_file_presence_message_level=MessageLevels.error,
        mimetype_mismatch_message_level=MessageLevels.error,
        bagit_info=None,
    ):
        """Initialize a new FS Api instance for a codebase release, including creating
        the SIP directory and bagging the contents if it does not already exist
        """
        fs_api = cls(
            codebase_release,
            system_file_presence_message_level=system_file_presence_message_level,
            mimetype_mismatch_message_level=mimetype_mismatch_message_level,
        )
        sip_dir = fs_api.sip_dir
        if not sip_dir.exists():
            os.makedirs(sip_dir, exist_ok=True)
            fs_api.get_or_create_sip_bag(bagit_info)
        return fs_api

    def create_or_update_codemeta(self, force=False):
        """
        Returns True if a codemeta.json file was created, False otherwise
        """
        path = self.codemeta_path
        if force or not path.exists():
            with path.open(mode="w", encoding="utf-8") as codemeta_out:
                codemeta_out.write(self.codemeta_contents)
            self.manifest.add_file(
                path.relative_to(self.sip_contents_dir).as_posix(),
                FileCategories.metadata,
            )
            return True
        return False

    def create_or_update_citation_cff(self, force=False):
        """
        Returns True if a CITATION.cff file was created, False otherwise
        """
        path = self.cff_path
        try:
            cff_contents = self.cff_contents
        except Exception as e:
            logger.exception(
                f"error generating CITATION.cff for release {self.release}: {e}"
            )
            return False
        if force or not path.exists():
            with path.open(mode="w", encoding="utf-8") as cff_out:
                cff_out.write(cff_contents)
            self.manifest.add_file(
                path.relative_to(self.sip_contents_dir).as_posix(),
                FileCategories.metadata,
            )
            return True
        return False

    def create_or_update_license(self, force=False):
        """
        Returns True if a LICENSE file was created, False otherwise
        """
        path = self.license_path
        if self.release.license and (force or not path.exists()):
            with path.open(mode="w", encoding="utf-8") as license_out:
                license_out.write(self.release.license_text)
            self.manifest.add_file(
                path.relative_to(self.sip_contents_dir).as_posix(),
                FileCategories.metadata,
            )
            return True
        return False

    def build_published_archive(self, force=False):
        self.create_or_update_codemeta(force=force)
        self.create_or_update_citation_cff(force=force)
        self.create_or_update_license(force=force)
        bag = self.get_or_create_sip_bag(self.bagit_info)
        self.validate_bagit(bag)
        self.build_archive(force=force)

    def build_review_archive(self):
        self.create_or_update_codemeta(force=True)
        self.create_or_update_citation_cff(force=True)
        self.create_or_update_license(force=True)
        shutil.make_archive(
            str(self.review_archivepath.with_suffix("")),
            format="zip",
            root_dir=str(self.sip_contents_dir),
        )
        return self.review_archivepath

    @property
    def codemeta_uri(self):
        return self.codemeta_path.relative_to(settings.LIBRARY_ROOT)

    @property
    def archive_uri(self):
        """returns the internal URI used by nginx to access this release's official archive package"""
        return self.archivepath.relative_to(settings.LIBRARY_ROOT)

    @property
    def review_archive_uri(self):
        """returns the internal uri used by nginx to access this release's review archive package"""
        return self.review_archivepath.relative_to(settings.LIBRARY_ROOT)

    @property
    def archive_size(self):
        return self.archivepath.stat().st_size

    @property
    def review_archive_size(self):
        return self.review_archivepath.stat().st_size

    def list(self, stage=StagingDirectories.sip, category=None):
        return [
            path
            for path, value in self.manifest.data.items()
            if category is None or value == category.name
        ]

    def list_sip_contents(self, path=None):
        root = self.sip_contents_dir
        manifest = self.manifest.data

        def directory_tree(directory):
            contents = []
            for child in sorted(directory.iterdir()):
                if child.is_dir():
                    contents.append(directory_tree(child))
                elif child.is_file():
                    relative = child.relative_to(root).as_posix()
                    contents.append(
                        {
                            "label": child.name,
                            "path": relative,
                            "category": manifest.get(
                                relative, FileCategories.metadata.name
                            ),
                        }
                    )
            return {
                "label": "archive-project-root"
                if directory == root
                else directory.name,
                "contents": contents,
            }

        return directory_tree(path or root)

    def check_category_file_exists(self, category):
        return any(
            (self.sip_contents_dir / path).is_file()
            for path in self.list(category=category)
        )

    def retrieve(self, stage, category, relpath):
        return self.get_sip_storage().open(str(relpath))

    def get_or_create_sip_bag(self, bagit_info=None):
        sip_dir = str(self.sip_dir)
        logger.info("creating bagit metadata at %s", sip_dir)
        bag = fs.make_bag(sip_dir, bagit_info)
        bag.save(manifests=True)
        return bag

    def build_aip(self, sip_dir: Optional[str] = None):
        logger.info("building aip")
        if sip_dir is None:
            sip_dir = str(self.sip_dir)
        shutil.rmtree(str(self.aip_dir), ignore_errors=True)
        shutil.copytree(sip_dir, str(self.aip_dir))

    def build_archive_at_dest(self, dest):
        logger.info("building archive")
        self.build_aip()
        if self.aip_contents_dir.exists():
            with zipfile.ZipFile(dest, "w") as archive:
                for root_path, dirs, file_paths in os.walk(str(self.aip_contents_dir)):
                    for file_path in file_paths:
                        path = Path(root_path, file_path)
                        archive.write(
                            str(path),
                            arcname=str(path.relative_to(self.aip_contents_dir)),
                        )
            logger.info("building archive succeeded")
            return True
        else:
            logger.error("building archive failed - no aip directory")
            return False

    def build_archive(self, force=False):
        if not self.archivepath.exists() or force:
            self.build_archive_at_dest(dest=str(self.archivepath))

    def create_or_update_metadata_files(self, force=False):
        self.create_or_update_codemeta(force=force)
        self.create_or_update_citation_cff(force=force)
        self.create_or_update_license(force=force)

    @transaction.atomic
    def rebuild_metadata(self):
        # Metadata jobs and uploads must not write the package concurrently.
        self.release = (
            type(self.release).objects.select_for_update().get(pk=self.release_id)
        )
        self.manifest = CategoryManifestManager(self.release)
        self.create_or_update_metadata_files(force=True)
        # only rebuild the archive package if it already exists
        if self.aip_dir.exists():
            self.build_archive(force=True)


def validate_package_path(name):
    path = Path(name)
    if (
        not name
        or "\\" in name
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:", name)
        or ".." in path.parts
        or path == Path(".")
    ):
        raise ValidationError("File paths must be relative and cannot contain '..'.")
    return name


def extract_manual_archive(archive, destination):
    """Preserve archive paths; reject links and traversal."""
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                validate_package_path(member.filename)
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValidationError("Archives cannot contain symbolic links.")
                if member.is_dir():
                    continue
                target = destination / member.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as bundle:
            for member in bundle:
                if member.isdir():
                    continue
                validate_package_path(member.name)
                if not member.isfile():
                    raise ValidationError(
                        "Archives can contain only regular files and directories."
                    )
                target = destination / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
    else:
        raise ValidationError("Upload a ZIP or tar archive, or individual files.")


class CodebaseReleaseFsApi(BaseCodebaseReleaseFsApi):
    """Manual packages keep their supplied paths. The SIP is the editable package.

    Legacy originals remain untouched for provenance; edits and review copies use
    the extracted package, so removing a file cannot resurrect it from an archive.
    """

    def _edit_package(self, edit):
        if not self.release.can_edit_originals or self.release.is_imported:
            raise ValidationError("Files cannot be edited for this release.")
        with TemporaryDirectory(dir=self.rootdir) as temporary:
            work = Path(temporary) / "data"
            backup = Path(temporary) / "previous"
            swapped = False
            try:
                with transaction.atomic():
                    release = (
                        type(self.release)
                        .objects.select_for_update()
                        .get(pk=self.release_id)
                    )
                    if not release.can_edit_originals or release.is_imported:
                        raise ValidationError(
                            "Files cannot be edited for this release."
                        )
                    manifest = CategoryManifestManager(release)
                    categories = dict(manifest.data)
                    shutil.copytree(self.sip_contents_dir, work)
                    edit(work, categories)
                    for directory in sorted(work.rglob("*"), reverse=True):
                        if directory.is_dir() and not any(directory.iterdir()):
                            directory.rmdir()
                    self.sip_contents_dir.rename(backup)
                    try:
                        work.rename(self.sip_contents_dir)
                    except Exception:
                        backup.rename(self.sip_contents_dir)
                        raise
                    swapped = True
                    manifest.update(categories)
                self.release.category_manifest = categories
            except Exception:
                if swapped:
                    shutil.rmtree(self.sip_contents_dir)
                    backup.rename(self.sip_contents_dir)
                raise

    def add(self, category=None, content=None, name=None):
        name = name or Path(content.name).name
        validate_package_path(name)
        msgs = MessageGroup()
        with TemporaryDirectory(dir=self.rootdir) as temporary:
            incoming = Path(temporary) / "incoming"
            incoming.mkdir()
            if fs.is_archive(name):
                archive = Path(temporary) / Path(name).name
                with archive.open("wb") as destination:
                    shutil.copyfileobj(content, destination)
                try:
                    extract_manual_archive(archive, incoming)
                except (
                    OSError,
                    ValueError,
                    zipfile.BadZipFile,
                    tarfile.TarError,
                ) as error:
                    raise ValidationError(
                        f"Cannot unpack this archive: {error}"
                    ) from error
            else:
                destination = incoming / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as target:
                    shutil.copyfileobj(content, target)
            paths = [path for path in incoming.rglob("*") if path.is_file()]
            paths = [
                path
                for path in paths
                if not fs.has_system_files(str(path.relative_to(incoming)))
            ]
            if not paths:
                raise ValidationError("The upload contains no usable files.")

            def add_files(work, categories):
                for source in paths:
                    relative = source.relative_to(incoming).as_posix()
                    target = work / relative
                    metadata_names = {
                        "CITATION.cff",
                        "codemeta.json",
                        "LICENSE",
                    }
                    if (
                        source.relative_to(incoming).parts[0] in metadata_names
                        and "/" in relative
                    ):
                        raise ValidationError(
                            "Root metadata paths must be files, not directories."
                        )
                    generated_metadata = relative in metadata_names
                    if target.exists() and not (
                        generated_metadata and target.is_file()
                    ):
                        raise ValidationError(
                            f"A file already exists at '{relative}'. "
                            "Remove it before uploading a replacement."
                        )
                    if any(parent.is_file() for parent in target.parents):
                        raise ValidationError(
                            f"A file blocks the directory for '{relative}'."
                        )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    categories[relative] = (
                        FileCategories.metadata.name
                        if generated_metadata
                        else category.name
                        if category
                        else self.manifest.guess_file_category(Path(relative))
                    )

            self._edit_package(add_files)
        return msgs

    def delete(self, category, relpath):
        name = str(relpath)
        validate_package_path(name)

        def remove_file(work, categories):
            if name not in categories or not (work / name).is_file():
                raise ValidationError("File not found in this package.")
            (work / name).unlink()
            del categories[name]

        self._edit_package(remove_file)
        return MessageGroup()

    def clear_category(self, category):
        def remove_files(work, categories):
            for name, value in list(categories.items()):
                if value == category.name:
                    (work / name).unlink(missing_ok=True)
                    del categories[name]

        self._edit_package(remove_files)

    def copy_originals(self, source_release):
        source = source_release.get_fs_api()

        def copy_files(work, categories):
            shutil.copytree(source.sip_contents_dir, work, dirs_exist_ok=True)
            categories.update(source.manifest.data)

        self._edit_package(copy_files)


class CategoryManifestManager:
    def __init__(self, release):
        self.release = release

    @property
    def data(self) -> dict:
        if self.release.category_manifest is None:
            self.backfill()
        return self.release.category_manifest

    def backfill(self):
        """Populate only missing manifests, without saving or rebuilding the release."""
        with transaction.atomic():
            release = (
                type(self.release).objects.select_for_update().get(pk=self.release.pk)
            )
            if release.category_manifest is None:
                if release.is_imported:
                    categories = dict(
                        release.imported_release_sync_state.category_manifest
                    )
                else:
                    root = Path(
                        settings.LIBRARY_ROOT,
                        str(release.codebase.uuid),
                        "releases",
                        str(release.pk),
                        "sip",
                        "data",
                    )
                    if not root.is_dir() and not release.can_edit_originals:
                        raise FileNotFoundError(
                            f"Release {release.pk} has no extracted package at {root}. "
                            "Check the library storage mount before backfilling."
                        )
                    categories = {}
                    for path in root.rglob("*"):
                        if path.is_file():
                            relative = path.relative_to(root)
                            category = (
                                relative.parts[0]
                                if len(relative.parts) > 1
                                else "metadata"
                            )
                            categories[relative.as_posix()] = (
                                category
                                if category
                                in {"code", "docs", "data", "results", "metadata"}
                                else "code"
                            )
                type(release).objects.filter(pk=release.pk).update(
                    category_manifest=categories
                )
                release.category_manifest = categories
            self.release.category_manifest = release.category_manifest

    def build(self, file_list: list[Path]):
        """generate a manifest from scratch from a list of files (normally sip.list()).
        This overwrites the existing manifest
        """
        manifest = {}
        for name in file_list:
            manifest[str(name)] = self.guess_file_category(name)
        self.update(manifest)

    @staticmethod
    def guess_file_category(name: Path) -> str:
        """Suggest documentation for known document extensions; otherwise code."""
        if (
            name.suffix == ".pdf"
            or name.suffix == ".docx"
            or name.suffix == ".doc"
            or name.suffix == ".md"
        ):
            return FileCategories.docs.name
        return FileCategories.code.name

    def update(self, manifest):
        # Skip save hooks: category edits must not rebuild metadata or archives.
        type(self.release).objects.filter(pk=self.release.pk).update(
            category_manifest=manifest
        )
        self.release.category_manifest = manifest

    def update_file_category(self, name, category: FileCategories):
        with transaction.atomic():
            release = (
                type(self.release).objects.select_for_update().get(pk=self.release.pk)
            )
            if not release.can_edit_originals:
                raise ValidationError("This release's files are locked.")
            manager = CategoryManifestManager(release)
            manifest = dict(manager.data)
            if name not in manifest:
                raise ValueError(f"file {name} not in manifest")
            manifest[name] = category.name
            manager.update(manifest)
            self.release.category_manifest = manifest

    def remove_file(self, name):
        manifest = self.data
        del manifest[name]
        self.update(manifest)

    def add_file(self, name, category: FileCategories = FileCategories.code):
        with transaction.atomic():
            release = (
                type(self.release).objects.select_for_update().get(pk=self.release.pk)
            )
            manager = CategoryManifestManager(release)
            manifest = dict(manager.data)
            manifest[name] = category.name
            manager.update(manifest)
            self.release.category_manifest = manifest

    def fix_from_list(self, file_list: list[Path]):
        """update the manifest to match the file list. This will add any files in the file list that are not in the
        manifest, and remove any files in the manifest that are not in the file list
        """
        manifest = self.data
        file_list_keys: set[str] = set()
        for name in file_list:
            key = str(name)
            file_list_keys.add(key)
            if key not in manifest:
                manifest[key] = self.guess_file_category(name)
        for key in list(manifest.keys()):
            if key not in file_list_keys:
                del manifest[key]
        self.update(manifest)


class ImportedCodebaseReleaseFsApi(BaseCodebaseReleaseFsApi):
    """
    File system API for managing an imported (i.e. from a GitHub release) codebase release.

    NOTE: This is not currently protected against concurrent file access but only the submitter can edit files
    associated with a codebase release at the moment. Will need to implement file locks if/when this assumption fails to
    hold
    """

    def __init__(
        self,
        codebase_release,
        system_file_presence_message_level=MessageLevels.error,
        mimetype_mismatch_message_level=MessageLevels.error,
    ):
        self.imported_release_sync_state = codebase_release.imported_release_sync_state
        if not self.imported_release_sync_state:
            raise ValueError("CodebaseRelease must be an imported release")
        super().__init__(
            codebase_release,
            system_file_presence_message_level,
            mimetype_mismatch_message_level,
        )
        self.imported_release_sync_state = codebase_release.imported_release_sync_state

    def download_archive(self, download_url: str, installation_token: str) -> Path:
        """Download a release package archive from a remote URL and
        places it in the originals stage directory"""
        originals_storage = self.get_originals_storage()
        if not os.path.exists(originals_storage.location):
            os.makedirs(originals_storage.location, exist_ok=True)
        originals_storage.clear()
        headers = {
            "Authorization": f"Bearer {installation_token}",
        }
        response = requests.get(download_url, headers=headers, stream=True)
        response.raise_for_status()
        cd = response.headers.get("content-disposition")
        if cd and "filename=" in cd:
            filename = re.findall("filename=(.+)", cd)[0]
        else:
            tag_name = self.imported_release_sync_state.tag_name
            filename = f"{tag_name}.zip"
        file_path = Path(originals_storage.location) / filename
        with file_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"downloaded imported release archive to {file_path}")
        return file_path

    def extract_to_sip(self, archive_path: Path):
        """Extract the downloaded release package archive into the SIP storage"""
        sip_storage = self.get_sip_storage()
        sip_storage.clear()
        if not zipfile.is_zipfile(str(archive_path)):
            raise ValueError("Archive file must be a zip archive")
        extract_zip_without_top_dir(archive_path, Path(sip_storage.location))
        logger.info(f"extracted imported release archive to {sip_storage.location}")

    def import_release_package(
        self, installation_token: str, download_url: str | None = None
    ) -> tuple[dict, dict]:
        """import a release archive from a remote URL (imported_release_sync_state.download_url by default)
        by downloading into the originals storage and extracting into the SIP storage.

        returns a tuple of dicts representing extracted metadata from known metadata files found in the archive,
        currently: (codemeta.json, CITATION.cff)

        NOTE: currently only supports zip archives
        """
        if download_url is None:
            download_url = self.imported_release_sync_state.download_url
        archive_path = self.download_archive(download_url, installation_token)
        self.extract_to_sip(archive_path)
        sip_contents = list(self.get_sip_storage().list())
        self.manifest.build(sip_contents)
        return self._extract_metadata_files(sip_contents)

    def _extract_metadata_files(self, sip_contents) -> tuple[dict, dict]:
        """searches the extracted archive for known metadata files and returns their contents

        returns a tuple of dicts, currently: (codemeta.json, CITATION.cff)
        """

        def find_file(file_list, target: str) -> Path | None:
            """
            search for a target file in the provided list of paths.
            target is case-insensitive
            """
            # check files in the root first
            for f in file_list:
                if len(f.parts) == 1 and f.name.lower() == target.lower():
                    return f
            for f in file_list:
                if f.name.lower() == target.lower():
                    return f
            return None

        codemeta_path = find_file(sip_contents, "codemeta.json")
        cff_path = find_file(sip_contents, "CITATION.cff")
        codemeta = None
        cff = None

        if codemeta_path:
            try:
                with self.get_sip_storage().open(str(codemeta_path), mode="r") as f:
                    file_content = f.read()
                parsed = json.loads(file_content)
                codemeta = parsed if isinstance(parsed, dict) else None
            except Exception:
                codemeta = None

        if cff_path:
            try:
                with self.get_sip_storage().open(str(cff_path), mode="r") as f:
                    file_content = f.read()
                parsed = yaml.safe_load(file_content)
                cff = parsed if isinstance(parsed, dict) else None
            except Exception:
                cff = None

        return codemeta, cff


class CodebaseGitRepositoryApi:
    """
    Manage a (local) git repository mirror of a codebase
    """

    FILE_SIZE_LIMIT = settings.GITHUB_INDIVIDUAL_FILE_SIZE_LIMIT
    MEGABYTE = 1024 * 1024
    FILE_SIZE_LIMIT_MB = FILE_SIZE_LIMIT / MEGABYTE
    DEFAULT_BRANCH_NAME = "main"
    RELEASE_BRANCH_PREFIX = "release/"

    def __init__(self, codebase):
        self.codebase = codebase
        self.repo_dir = Path(self.codebase.base_git_dir).absolute()

    @property
    def committer(self):
        return Actor("CoMSES Net", settings.EDITOR_EMAIL)

    @property
    def author(self):
        profile = self.codebase.submitter.member_profile
        author_email = (
            f"{profile.github_username}@users.noreply.github.com"
            if profile.github_username
            else profile.email
        )
        return Actor(profile.name, author_email)

    def get_release_branch_name(self, release):
        return f"{self.RELEASE_BRANCH_PREFIX}{release.version_number}"

    @classmethod
    def check_file_sizes(cls, codebase):
        releases = codebase.ordered_releases_list(internal_only=True)
        for release in releases:
            release_fs_api = release.get_fs_api()
            sip_storage = release_fs_api.get_sip_storage()
            for file in sip_storage.list(absolute=True):
                if file.stat().st_size > cls.FILE_SIZE_LIMIT:
                    file_size_mb = file.stat().st_size / cls.MEGABYTE
                    raise ValidationError(
                        f"File {file} is too large ({file_size_mb}MB), individual files must be under {cls.FILE_SIZE_LIMIT_MB}MB"
                    )

    def initialize(self, should_exist=False):
        """
        initialize the git repository or connect to an existing one

        :param should_exist: if True, raise an error if the repository does not exist
        """
        if not self.repo_dir.exists():
            if should_exist:
                raise RuntimeError(f"Repository {self.repo_dir} does not exist")
            self.repo_dir.mkdir(parents=True)
        try:
            self.repo = Repo(self.repo_dir)
        except InvalidGitRepositoryError:
            if should_exist:
                raise RuntimeError(f"Repository {self.repo_dir} does not exist")
            self.repo = Repo.init(
                self.repo_dir, initial_branch=self.DEFAULT_BRANCH_NAME
            )
        except Exception as e:
            logger.exception(e)
            raise RuntimeError(f"Failed to initialize git repository")

    def checkout_main(self, update_main_git_ref_sync_state=False):
        """checkout the default (main) branch and create/update the git ref sync state if requested"""
        self.repo.git.checkout(self.DEFAULT_BRANCH_NAME)
        if update_main_git_ref_sync_state:
            main_state = self.codebase.get_or_create_main_git_ref_sync_state(
                self.DEFAULT_BRANCH_NAME
            )
            main_state.record_build(commit_sha=self.repo.head.commit.hexsha)

    def clear_existing_files(self):
        """
        clear any existing files in the working tree (tracked or untracked) besides .git
        """
        for item in self.repo_dir.iterdir():
            if item.name != ".git":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                self.repo.index.remove(
                    [str(item.relative_to(self.repo_dir))],
                    working_tree=True,
                    r=True,
                )

    def add_release_files(self, release):
        """
        copy over submission package files for a release to the working tree of the git repo
        starting from a clean directory by removing all files except .git/
        """
        release_fs_api: CodebaseReleaseFsApi = release.get_fs_api()
        sip_storage = release_fs_api.get_sip_storage()
        self.clear_existing_files()
        # copy over files from the sip storage and add to the index
        # FIXME: consider moving this copy all operation to the CodebaseReleaseStorage class
        for file in sip_storage.list(absolute=True):
            rel_path = file.relative_to(sip_storage.location)
            dest_path = self.repo_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, dest_path)
            self.repo.index.add([str(rel_path)])

    def add_readme(self, release):
        """
        add a readme file to the repository root. If one already exists somewhere, move it.
        Otherwise, generate one from a template
        """
        release_fs_api: CodebaseReleaseFsApi = release.get_fs_api()
        sip_storage = release_fs_api.get_sip_storage()
        readme_pattern = re.compile(
            r"(?i)^readme(?:\.(?:markdown|mdown|mkdn|md|textile|rdoc|org|creole|mediawiki|wiki|rst|asciidoc|adoc|asc|pod|txt))?$"
        )
        for file in sip_storage.list(absolute=True):
            # check for an existing readme and duplicate it to the repo root
            # for github to recognize. Otherwise, we'll generate one later
            if readme_pattern.match(file.name):
                shutil.copy(file, self.repo_dir / file.name)
                self.repo.index.add([file.name])
                return
        readme_content = f"# {self.codebase.title}\n\n{self.codebase.description.raw}\n"
        self._add_single_file("README.md", readme_content)

    def _add_single_file(self, filename, content: str, overwrite=False):
        dest_path = self.repo_dir / filename
        if not dest_path.exists() or overwrite:
            with dest_path.open("w") as f:
                f.write(content)
            self.repo.index.add([filename])

    def commit_release(self, release):
        """
        commit the the release and tag it, should only be called after adding all necessary files
        """
        # make sure the commit goes to main, then create the release branch later
        # unless this is the first commit
        if self.DEFAULT_BRANCH_NAME in self.repo.heads:
            self.checkout_main()
        commit_msg = (
            f"Release {release.version_number}\n\n{release.release_notes.raw}\n"
        )
        for rc in release.coauthor_release_contributors:
            contributor = rc.contributor
            email = ""
            # try to use the co-author's github account email, otherwise just leave it blank
            if contributor.user and contributor.user.member_profile.github_username:
                email = f"{contributor.user.member_profile.github_username}@users.noreply.github.com"
            commit_msg += f"\nCo-authored-by: {contributor.name} <{email}>"
        commit = self.repo.index.commit(
            message=commit_msg,
            committer=self.committer,
            author=self.author,
            author_date=release.last_published_on,
        )
        tag_name = release.version_number
        self.repo.create_tag(tag_name)
        return commit, tag_name

    def create_release_branch(self, release, commit):
        """
        create a new branch for the release
        """
        release_branch_name = self.get_release_branch_name(release)
        self.repo.create_head(release_branch_name, commit)
        return release_branch_name

    def build_release_refs(self, release):
        """
        commit the release, create a branch/tag, and create the git ref sync state
        """
        self.add_release_files(release)
        self.add_readme(release)
        commit, tag_name = self.commit_release(release)
        branch_name = self.create_release_branch(release, commit)
        # create git ref sync state for the release
        release.get_or_create_git_ref_sync_state().record_build(
            commit.hexsha,
            tag_name=tag_name,
            branch_name=branch_name,
        )

    def update_release_branch(self, release) -> Repo | None:
        """
        update a release branch with new metadata, merging back into main (fast-forward)
        if it is the latest release

        this ONLY updates metadata files and does not add
        changes to the code, docs, etc. as it is assumed that any synced releases are published
        and frozen

        returns None if no changes were made, otherwise returns the updated repo
        """
        self.initialize(should_exist=True)
        release_branch_name = self.get_release_branch_name(release)
        # determine whether this is the latest release (i.e. points to the
        # same thing as main) and should merge back into main
        release_branch = self.repo.heads[release_branch_name]
        main_branch = self.repo.heads[self.DEFAULT_BRANCH_NAME]
        merge_into_main = (main_branch.commit == release_branch.commit) and (
            main_branch.commit == self.repo.head.commit
        )

        self.repo.git.checkout(release_branch_name)
        self.add_release_files(release)
        self.add_readme(release)

        # check for changes before committing
        if not self.repo.is_dirty():
            self.checkout_main()
            return None

        commit_msg = f"Update metadata for release {release.version_number}"
        commit = self.repo.index.commit(
            message=commit_msg,
            committer=self.committer,
            author=self.author,
            author_date=timezone.now(),
        )
        # update git ref sync state for this release to reflect new commit
        release.get_or_create_git_ref_sync_state().record_build(commit.hexsha)
        if merge_into_main:
            self.checkout_main()
            try:
                self.repo.git.merge("--ff-only", release_branch_name)
                self.checkout_main(update_main_git_ref_sync_state=True)
            except Exception as e:
                logger.error(
                    f"Unexpected divergence when trying to merge {release_branch_name} into {self.DEFAULT_BRANCH_NAME}: {e}"
                )
        self.checkout_main()

        return Repo(self.repo_dir)

    def append_releases(self, releases=None) -> Repo:
        """
        add new releases to the git repository.
        releases must be newer/higher than the latest mirrored release so that they can be added on top

        this should only be used if no releases have been removed or otherwise modified since these require
        rewriting history and this method strictly appends new releases

        :param releases: list of releases to append, if None, all unmirrored releases will be appended
        """
        self.check_file_sizes(self.codebase)
        if not releases:
            # select internal public releases without a build state
            releases = self.codebase.releases_without_git_ref_sync_state()
        if not releases:
            # nothing to do, return the existing repo
            return Repo(self.repo_dir)
        self.initialize(should_exist=True)
        # make sure the releases are higher than the latest mirrored release
        latest_built_state = self.codebase.latest_release_git_ref_sync_state()
        if latest_built_state is not None:
            if not all(
                Version(release.version_number)
                > Version(latest_built_state.release.version_number)
                for release in releases
            ):
                raise ValueError(
                    "Releases must be higher than the latest mirrored release to append"
                )
        # make sure the releases are ordered by version number
        releases = sorted(releases, key=lambda r: Version(r.version_number))
        # append releases to the git repo by adding files, committing, and creating a branch
        for release in releases:
            self.build_release_refs(release)
        self.checkout_main(update_main_git_ref_sync_state=True)
        return Repo(self.repo_dir)

    def build(self) -> Repo:
        """
        builds or rebuilds the git repository from codebase releases

        this will create an entirely new repository and should only be used if we are creating the
        mirror for the first time or need to rebuild the entire history
        """
        self.check_file_sizes(self.codebase)
        releases = self.codebase.ordered_releases_list(internal_only=True)
        if not releases:
            raise ValidationError("Must have at least one public release to build from")
        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir)
        self.initialize()
        for release in releases:
            self.build_release_refs(release)
        self.checkout_main(update_main_git_ref_sync_state=True)
        return Repo(self.repo_dir)

    def update_or_build(self) -> Repo:
        # if the repo doesn't exist or is empty, build/rebuild
        if not self.repo_dir.exists() or not self.repo_dir.joinpath(".git").exists():
            return self.build()
        # if no successful build states exist, rebuild
        if not self.codebase.latest_release_git_ref_sync_state():
            return self.build()
        return self.append_releases()

    def dirs_equal(self, dir1: Path, dir2: Path, ignore=[".git"]):
        """
        check if two directories are equal by recursively comparing their contents
        excluding the files in the ignore list (default is just .git)

        this will likely go unused in favor of a more efficient method for checking if a
        release mirror (commit) is up to date
        """
        dir1 = Path(dir1)
        dir2 = Path(dir2)
        comparison = filecmp.dircmp(dir1, dir2, ignore=ignore)
        if (
            comparison.left_only
            or comparison.right_only
            or comparison.diff_files
            or comparison.funny_files
        ):
            return False
        else:
            for subdir in comparison.common_dirs:
                if not self.dirs_equal(dir1 / subdir, dir2 / subdir):
                    return False
            return True


def import_archive(codebase_release, nested_code_folder_name, fs_api=None):
    """currently only used for tests"""
    if fs_api is None:
        fs_api = codebase_release.get_fs_api()
    nested_code_folder_name = str(nested_code_folder_name)
    archive_name = f"{nested_code_folder_name}.zip"
    shutil.make_archive(nested_code_folder_name, "zip", nested_code_folder_name)
    with open(archive_name, "rb") as f:
        msgs = fs_api.add(FileCategories.code, content=f, name="nestedcode.zip")
    return msgs


def extract_zip_without_top_dir(zip_path: Path, extract_to: Path):
    """extract a zip archive to a directory, removing the top-level directory"""
    with zipfile.ZipFile(zip_path, "r") as z:
        all_names = [m.filename for m in z.infolist()]
        top_level = os.path.commonprefix(all_names).rstrip("/")
        # remove the top-level dir from each path and extract
        for member in z.infolist():
            relative_path = os.path.relpath(member.filename, top_level)
            if relative_path == ".":  # skip top-level dir
                continue
            target_path = extract_to / relative_path
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with target_path.open("wb") as f:
                    f.write(z.read(member))
