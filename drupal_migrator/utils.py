import mimetypes
from PIL import Image

import logging

logger = logging.getLogger(__name__)

def get_first_field(obj, field_name, attribute_name='value', default=''):
    try:
        return obj[field_name]['und'][0][attribute_name] or default
    except:
        return default


def get_field_attributes(json_object, field_name, attribute_name='value', default=None):
    if default is None:
        default = []
    try:
        return [obj[attribute_name] for obj in json_object[field_name]['und']]
    except:
        return default


def get_field(obj, field_name, default=''):
    try:
        return obj[field_name]['und'] or default
    except:
        return default


def is_media(path: str):
    logger.debug("checking media type of %s", path)
    mimetype = mimetypes.guess_type('file:/{0}'.format(path))
    if mimetype[0] and mimetype[0].startswith(('image', 'video')):
        return True
    try:
        Image.open(path)
        return True
    except IOError:
        logger.exception("path %s wasn't quite imagelike enough")
    return False
