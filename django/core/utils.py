import pathlib

import bleach
import markdown
from django.core.files.images import ImageFile
from wagtail.wagtailimages.models import Image

ALLOWED_TAGS = bleach.ALLOWED_TAGS + ['p', 'h1', 'h2', 'h3', 'h4', 'pre', 'br', 'div', 'span']

DEFAULT_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists',
    'markdown.extensions.smarty',
    'markdown.extensions.toc',
#    'markdown.extensions.wikilinks',
]


def markdown_to_sanitized_html(md: str, extensions=None):
    if extensions is None:
        extensions = DEFAULT_MARKDOWN_EXTENSIONS
    html = markdown.markdown(
        md,
        extensions=extensions
    )
    return bleach.clean(bleach.linkify(html), tags=ALLOWED_TAGS)


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