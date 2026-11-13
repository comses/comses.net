import imghdr
import logging
import mimetypes
import os
import pathlib
import shutil
import stat
import time
import zipfile

import bagit
import rarfile
from django.conf import settings
from django.core.files.images import ImageFile
from wagtail.images.models import Image

logger = logging.getLogger(__name__)

SYSTEM_FILES = (
    "__macosx",
    ".ds_store",
    ".svn",
    ".git",
    ".hg",
    "thumbs.db",
    "cvs",
    ".trashes",
)


def is_archive(path: str):
    """
    Returns the guessed type of the archive or None
    :param path: string path to the file to be checked
    :return: archive's mimetype string (based on file extension, not inspecting the contents) or None if not an archive
    """
    mimetype = mimetypes.guess_type(path)
    if mimetype[0] and mimetype[0].endswith(("tar", "zip", "rar")):
        return mimetype[0]
    return None


def is_image(path: str):
    try:
        filetype = imghdr.what(path)
        return filetype in settings.ACCEPTED_IMAGE_TYPES
    except Exception:
        return None


def is_media(path: str):
    """
    :param path: string path to the file to be checked
    :return: media mimetype string / format or None
    """
    mimetype = mimetypes.guess_type(path)
    if mimetype[0] and mimetype[0].startswith(("image", "video")):
        return mimetype[0]
    else:
        try:
            with Image.open(path) as image:
                return image.format
        except IOError:
            logger.exception("Path was not an image")
    return None


def has_system_files(path: str) -> bool:
    for part in set(pathlib.Path(path).parts):
        if is_system_file(part):
            return True
    return False


def is_system_file(filename: str) -> bool:
    """
    :param filename: candidate filename to test
    :return: True if filename is a osx system file or appears to be a backup file
    """
    if filename:
        return (
            filename.lower() in SYSTEM_FILES
            or filename.startswith("~")
            or filename.endswith("~")
            or filename.startswith("._")
        )
    logger.warning("tried to check if an empty string is a system file")
    return False


def rm_system_files(base_dir):
    """
    Removes all files that appear to be system or backup files from the base directory passed in as root.
    :param base_dir: base directory for all candidate filenames
    :return: a list of removed system files, if any
    """
    removed_files = []
    for root, dirs, files in os.walk(base_dir, topdown=True):
        for candidate in dirs + files:
            if is_system_file(candidate):
                full_path = os.path.join(base_dir, candidate)
                removed_files.append(full_path)
                if candidate in dirs:
                    shutil.rmtree(full_path)
                    dirs.remove(candidate)
                else:
                    os.remove(full_path)
    return removed_files


class ArchiveLimitError(ValueError):
    """An archive exceeded its configured resource budget."""


class ArchiveBudget:
    """Bound declared sizes and actual output; deadlines are cooperative."""

    def __init__(self):
        self.input_limit = settings.ARCHIVE_MAX_INPUT_BYTES
        self.total_limit = settings.ARCHIVE_MAX_TOTAL_BYTES
        self.file_limit = settings.ARCHIVE_MAX_FILE_BYTES
        self.member_limit = settings.ARCHIVE_MAX_MEMBERS
        self.depth_limit = settings.ARCHIVE_MAX_PATH_DEPTH
        limits = (
            self.input_limit,
            self.total_limit,
            self.file_limit,
            self.member_limit,
            self.depth_limit,
            settings.ARCHIVE_MAX_SECONDS,
        )
        if any(limit <= 0 for limit in limits):
            raise ArchiveLimitError("Archive limits must be positive")
        self.deadline = time.monotonic() + settings.ARCHIVE_MAX_SECONDS
        self.members = 0
        self.declared_bytes = 0
        self.written_bytes = 0

    def check_time(self):
        if time.monotonic() >= self.deadline:
            raise ArchiveLimitError("Archive processing time limit exceeded")

    def check_input(self, filename):
        self.check_time()
        if pathlib.Path(filename).stat().st_size > self.input_limit:
            raise ArchiveLimitError(f"Archive input size exceeds {self.input_limit} bytes")

    def add_member(self, name, size):
        self.check_time()
        self.members += 1
        if self.members > self.member_limit:
            raise ArchiveLimitError(f"Archive member count exceeds {self.member_limit}")
        if len(pathlib.PurePosixPath(name).parts) > self.depth_limit:
            raise ArchiveLimitError(f"Archive path depth exceeds {self.depth_limit} components")
        if size < 0 or size > self.file_limit:
            raise ArchiveLimitError(f"Archive member size must be between 0 and {self.file_limit} bytes")
        self.declared_bytes += size
        if self.declared_bytes > self.total_limit:
            raise ArchiveLimitError(f"Archive total extracted size exceeds {self.total_limit} bytes")

    def copy(self, source, destination):
        file_bytes = 0
        while True:
            self.check_time()
            chunk = source.read(64 * 1024)
            self.check_time()
            if not chunk:
                return
            file_bytes += len(chunk)
            if file_bytes > self.file_limit:
                raise ArchiveLimitError(f"Archive individual file size exceeds {self.file_limit} bytes")
            if self.written_bytes + len(chunk) > self.total_limit:
                raise ArchiveLimitError(f"Archive total extracted size exceeds {self.total_limit} bytes")
            destination.write(chunk)
            self.written_bytes += len(chunk)


def archive_member_path(name, destination):
    """Validate an archive path before any extraction or path normalization."""
    path = pathlib.PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name or pathlib.PureWindowsPath(name).drive:
        raise ValueError("Archive member paths must be relative and stay within the extraction directory")
    target = pathlib.Path(destination).joinpath(*path.parts)
    if not target.resolve().is_relative_to(pathlib.Path(destination).resolve()):
        raise ValueError("Archive member path escapes the extraction directory")
    return target


def unrar(archive_path, dst_dir: str):
    budget = ArchiveBudget()
    budget.check_input(archive_path)
    with rarfile.RarFile(archive_path) as rf:
        members = rf.infolist()
        # Validate the entire archive before creating files or links.
        for member in members:
            budget.add_member(member.filename, member.file_size)
            archive_member_path(member.filename, dst_dir)
            if member.is_symlink() or member.file_redir or not (member.is_file() or member.is_dir()):
                raise ValueError("RAR archive members must be regular files or directories without redirections")
        for member in members:
            budget.check_time()
            target = archive_member_path(member.filename, dst_dir)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with rf.open(member) as source, target.open("wb") as destination:
                    budget.copy(source, destination)
        budget.check_time()


def extract_zip(zip_path, extract_to, strip_top_dir=False, overwrite=True):
    budget = ArchiveBudget()
    budget.check_input(zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.infolist()
        paths = []
        for member in members:
            budget.add_member(member.filename, member.file_size)
            archive_member_path(member.filename, extract_to)
            file_type = stat.S_IFMT(member.external_attr >> 16)
            if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("ZIP archive members must be regular files or directories")
            paths.append(pathlib.Path(member.filename))

        roots = {path.parts[0] for path in paths if path.parts}
        strip_root = (
            strip_top_dir
            and len(roots) == 1
            and all(len(path.parts) > 1 or member.is_dir() for member, path in zip(members, paths))
        )
        targets = []
        for member, path in zip(members, paths):
            relative_path = pathlib.Path(*path.parts[1:]) if strip_root else path
            if relative_path == pathlib.Path("."):
                if not member.is_dir():
                    raise ValueError("ZIP file member must have a filename")
                continue
            targets.append((member, archive_member_path(relative_path.as_posix(), extract_to)))

        for member, target in targets:
            budget.check_time()
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb" if overwrite else "xb") as destination:
                    budget.copy(source, destination)
        budget.check_time()


def make_bag(path, info: dict = None):
    # first check if there's already a bag at this path - if so, use it.
    try:
        return bagit.Bag(path)
    except bagit.BagError:
        logger.info("unable to initialize bag at %s - making a new one", path)

    # unable to create a bag from an existing bag
    if info is None:
        info = {}
    return bagit.make_bag(path, info)


def clean_directory(path):
    for fs in os.scandir(path):
        if fs.is_dir():
            shutil.rmtree(os.path.join(path, fs.name), ignore_errors=True)
        elif fs.is_file():
            os.remove(os.path.join(path, fs.name))


def get_canonical_image(title, path, user):
    _image_path = pathlib.Path(path)
    if Image.objects.filter(title=title).exists():
        _image = Image.objects.get(title=title)
    else:
        _image = Image.objects.create(title=title, file=ImageFile(_image_path.open("rb")), uploaded_by_user=user)
    return _image
