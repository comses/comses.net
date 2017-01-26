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


def is_imageish(path: str):
    mimetype = mimetypes.guess_type(path)
    if mimetype[0].startswith('image'):
        return True
    try:
        Image.open(path)
    except IOError:
        logger.debug("path %s to be an image")
    return False

