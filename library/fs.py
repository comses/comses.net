import logging
import mimetypes
from PIL import Image

import shutil

logger = logging.getLogger(__name__)


def is_archive(path: str):
    logger.debug("checking archive-ness of %s", path)
    mimetype = mimetypes.guess_type(path)
    if mimetype[0] and mimetype[0].endswith(('tar', 'zip', 'rar')):
        return mimetype[0]
    return False


def is_media(path: str):
    logger.debug("checking media type of %s", path)
    mimetype = mimetypes.guess_type('file:/{0}'.format(path))
    if mimetype[0] and mimetype[0].startswith(('image', 'video')):
        return mimetype[0]
    try:
        Image.open(path)
        return mimetype[0]
    except IOError:
        logger.exception("path %s wasn't quite imagelike enough")
    return False


def is_system_file(filename: str):
    logger.debug("checking if %s is a system file", filename)
    return filename in ('__MACOSX', '.DS_Store')


def rm_system_files(path):
    ''' returns True if path was a system file and deleted, False otherwise'''
    if is_system_file(path):
        shutil.rmtree(path)
        return True
    return False
