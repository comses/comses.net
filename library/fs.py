import bagit
import logging
import mimetypes
import os
import rarfile
import shutil

from PIL import Image

logger = logging.getLogger(__name__)


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


def is_system_file(filename: str) -> bool:
    """
    :param filename: candidate filename to test
    :return: True if filename is a osx system file or appears to be a backup file
    """
    return filename in ('__MACOSX', '.DS_Store') or filename.startswith('~') or filename.endswith('~')


def rm_system_files(base_dir, candidates):
    """
    Removes all files that appear to be system or backup files from the base directory passed in as root.
    :param base_dir: base directory for all candidate filenames
    :param candidates: list of candidate filenames
    :return: a list of removed system files, if any
    """
    removed_files = []
    for f in candidates:
        if is_system_file(f):
            full_path = os.path.join(base_dir, f)
            removed_files.append(full_path)
            if os.path.isdir(full_path):
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