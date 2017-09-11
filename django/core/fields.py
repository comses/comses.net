import bleach
import html2text
import markdown
from django.db import models
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


def sanitize_html(html):
    return bleach.clean(html, tags=['a', 'b', 'i', 'u', 'p',
                                    'br', 'hr',
                                    'ul', 'ol', 'li',
                                    'code',
                                    'table', 'thead', 'tbody', 'tfoot', 'col', 'colgroup', 'th', 'tr', 'td',
                                    'h1', 'h2', 'h3'])


def validate_markdown(value):
    if value is None:
        return
    html = markdown.markdown(value)
    bleached_html = sanitize_html(html)
    if html != bleached_html:
        raise ValidationError('Markdown not sanitized: {}'.format(value))


class MarkdownField(models.TextField):
    description = "Sanitized Markdown"

    def to_python(self, value):
        validate_markdown(value)
        return value
