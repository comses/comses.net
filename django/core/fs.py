import imghdr
import logging
import mimetypes
import os
import pathlib
import shutil

import bagit
import rarfile
from PIL import Image
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.images import ImageFile
from wagtail.images.models import Image

logger = logging.getLogger(__name__)


def is_subpath(basepath: pathlib.Path, path: pathlib.Path):
    if basepath not in path.parents:
        raise SuspiciousFileOperation(
            'The joined path ({}) is located outside of the base path '
            'component ({})'.format(str(path), str(basepath)))


def is_archive(path: str):
    """
    Returns the guessed type of the archive or None
    :param path: string path to the file to be checked
    :return: archive's mimetype string (based on file extension, not inspecting the contents) or None if not an archive
    """
    mimetype = mimetypes.guess_type(path)
    if mimetype[0] and mimetype[0].endswith(('tar', 'zip', 'rar')):
        return mimetype[0]
    return None


def is_image(path: str):
    try:
        return imghdr.what(path)
    except:
        return None


def is_media(path: str):
    """
    :param path: string path to the file to be checked
    :return: media mimetype string / format or None
    """
    mimetype = mimetypes.guess_type(path)
    if mimetype[0] and mimetype[0].startswith(('image', 'video')):
        return mimetype[0]
    else:
        try:
            with Image.open(path) as image:
                return image.format
        except IOError:
            logger.exception("Path was not an image")
    return None


SYSTEM_FILES = ('__macosx', '.ds_store', '.svn', '.git', '.hg', 'thumbs.db', 'cvs', '.trashes')


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
        return filename.lower() in SYSTEM_FILES or filename.startswith('~') or filename.endswith('~') or filename.startswith('._')
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


def unrar(archive_path, dst_dir: str):
    with rarfile.RarFile(archive_path) as rf:
        rf.extractall(dst_dir)


def make_bag(path, info: dict):
    try:
        return bagit.Bag(path)
    except bagit.BagError as e:
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
        _image = Image.objects.create(
            title=title,
            file=ImageFile(_image_path.open('rb')),
            uploaded_by_user=user)
    return _image