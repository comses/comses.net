import pathlib

import bleach
import markdown
from django.core.files.images import ImageFile
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