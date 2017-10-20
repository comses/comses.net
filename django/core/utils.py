from dateutil.parser import parse as _parse_datetime, tz

from django.conf import settings
from django.core.files.images import ImageFile

import pathlib

from wagtail.wagtailimages.models import Image


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


def parse_datetime(timestr: str):
    tzinfo = tz.gettz(settings.TIME_ZONE)
    if timestr:
        dt = _parse_datetime(timestr)
        dt.replace(tzinfo=tzinfo)
        return dt
    return None