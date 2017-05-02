import logging
import pathlib
from datetime import datetime
import pytz
import re

from django.core.files.images import ImageFile
from wagtail.wagtailimages.models import Image

logger = logging.getLogger(__name__)


def get_first_field(obj, field_name, attribute_name='value', default=''):
    try:
        return obj[field_name]['und'][0][attribute_name].strip() or default
    except:
        return default


def get_field_attributes(json_object, field_name, attribute_name='value', default=None):
    if default is None:
        default = []
    try:
        return [obj[attribute_name].strip() for obj in json_object[field_name]['und']]
    except:
        return default


def get_field(obj, field_name, default=''):
    try:
        return obj[field_name]['und'] or default
    except:
        return default


def to_datetime(drupal_datetime_string: str, tz=pytz.UTC):
    if drupal_datetime_string.strip():
        # majority of incoming Drupal datetime strings are unix timestamps, e.g.,
        # http://drupal.stackexchange.com/questions/45443/why-timestamp-format-was-chosen-for-users-created-field
        try:
            return datetime.fromtimestamp(float(drupal_datetime_string), tz=tz)
        except:
            logger.warning("Could not convert as a timestamp: %s", drupal_datetime_string)
        # occasionally they are also date strings like '2010-08-01 00:00:00'
        try:
            return datetime.strptime(drupal_datetime_string, '%Y-%m-%d %H:%M:%S')
        except:
            logger.exception("Expecting a datetime string or a float / unix timestamp but received: %s ", drupal_datetime_string)
        # give up, fall through and return None
    return None


def get_canonical_image(title=None, path=None, user=None):
    _image_path = pathlib.Path(path)
    if Image.objects.filter(title=title).exists():
        _image = Image.objects.get(title=title)
    else:
        _image = Image.objects.create(
            title=title,
            file=ImageFile(_image_path.open('rb')),
            uploaded_by_user=user)
    return _image