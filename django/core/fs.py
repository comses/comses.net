import imghdr
import logging
import mimetypes
import os
import shutil

import bagit
import pathlib
import rarfile
from PIL import Image
from django.core.exceptions import SuspiciousFileOperation

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


SYSTEM_FILES = ('__MACOSX', '.DS_Store', '.svn', '.git', '.hg')


def has_macosx_dir(filename: str) -> bool:
    path = pathlib.Path(filename)
    return '__MACOSX' in path.parts


def is_system_file(filename: str) -> bool:
    """
    :param filename: candidate filename to test
    :return: True if filename is a osx system file or appears to be a backup file
    """
    return filename in ('__MACOSX', '.DS_Store') or filename.startswith('~') or filename.endswith('~')


def rm_system_files(base_dir, dirs, files):
    """
    Removes all files that appear to be system or backup files from the base directory passed in as root.
    :param base_dir: base directory for all candidate filenames
    :param candidates: list of candidate filenames
    :return: a list of removed system files, if any
    """
    removed_files = []
    for candidate in dirs + files:
        if is_system_file(candidate):
            full_path = os.path.join(base_dir, candidate)
            removed_files.append(full_path)
            if candidate in dirs:
                shutil.rmtree(full_path)
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
