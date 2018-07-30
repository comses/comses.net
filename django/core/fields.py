import logging

import bleach
import markdown
from django.utils.html import linebreaks, escape
from jinja2.utils import urlize
from markupfield.fields import MarkupField

from .widgets import MarkdownTextarea

logger = logging.getLogger(__name__)


ALLOWED_TAGS = bleach.ALLOWED_TAGS + [
    'p', 'h1', 'h2', 'h3', 'h4', 'pre', 'br', 'hr', 'div', 'span', 'footer',
    'img', 'table', 'thead', 'tbody', 'tfoot', 'col', 'colgroup', 'th', 'tr', 'td'
]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES,
                          **{'*': ['name', 'id', 'class'], 'img': ['alt', 'src']})

DEFAULT_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists',
    'markdown.extensions.smarty',
    'markdown.extensions.toc',
    #    'markdown.extensions.wikilinks',
]


def render_sanitized_markdown(md_text: str, extensions=None):
    if extensions is None:
        extensions = DEFAULT_MARKDOWN_EXTENSIONS
    html = markdown.markdown(
        md_text,
        extensions=extensions
    )
    return sanitize_html(html)


def sanitize_html(html: str):
    return bleach.clean(bleach.linkify(html), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)


class MarkdownField(MarkupField):

    CUSTOM_RENDERERS = (
        ('markdown', render_sanitized_markdown),
        ('html', sanitize_html),
        ('plain', lambda markup: linebreaks(urlize(escape(markup)))),
        ('', lambda markup: markup),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault('blank', True)
        kwargs.update(
            default_markup_type='markdown',
            markup_choices=MarkdownField.CUSTOM_RENDERERS,
        )
        super(MarkdownField, self).__init__(**kwargs)

    def get_searchable_content(self, value):
        return self.get_prep_value(value)

    def formfield(self, **kwargs):
        defaults = {'widget': MarkdownTextarea}
        defaults.update(kwargs)
        return super(MarkupField, self).formfield(**defaults)