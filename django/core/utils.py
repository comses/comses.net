import pathlib
from distutils.util import strtobool

from dateutil import parser
from django.core.files.images import ImageFile
from django.utils import timezone
from wagtail.images.models import Image


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


def parse_datetime(datetime_str: str):
    """
    Parses a datetime string with optional timezone encoding and returns a timezone aware datetime.
    If an empty string is passed in, returns None. If an invalid datetime string is given a ValueError will be raised
    http://dateutil.readthedocs.io/en/stable/parser.html
    """
    if datetime_str:
        dt = parser.parse(datetime_str)
        if dt.tzinfo is None:
            return timezone.make_aware(dt)
        return dt
    return None


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        print("Invalid response ", response_as_bool, ". Please confirm with yes (y) or no (n).")
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)
    return True