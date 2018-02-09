import logging
import re
from datetime import datetime
from pathlib import Path

import pytz

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
            # logger.debug("Could not convert as a timestamp: %s", drupal_datetime_string)
            pass
        # occasionally they are also date strings like '2010-08-01 00:00:00'
        try:
            return datetime.strptime(drupal_datetime_string, '%Y-%m-%d %H:%M:%S')
        except:
            logger.exception("Expecting a datetime string or a float / unix timestamp but received: %s ", drupal_datetime_string)
        # give up, fall through and return None
    return None

MODELVERSION_REGEX = re.compile('\d+')

def model_version_has_files(model_path):
    for p in Path(model_path).rglob('*'):
        if p.is_file():
            return True
    return False


def is_version_dir(candidate: Path):
    return candidate.is_dir() and candidate.name.startswith('v') and MODELVERSION_REGEX.search(
        candidate.name)