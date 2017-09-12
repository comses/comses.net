import bleach
import html2text
import markdown
from django.db import models
from django.core.exceptions import ValidationError
import logging
import difflib
import io

logger = logging.getLogger(__name__)


def sanitize_html(html):
    return bleach.clean(html,
                        tags=[
                            'a', 'b', 'i', 'u', 'p', 'em', 'strong',
                            'br', 'hr',
                            'ul', 'ol', 'li',
                            'pre', 'code', 'blockquote',
                            'table', 'thead', 'tbody', 'tfoot', 'col', 'colgroup', 'th', 'tr', 'td',
                            'h1', 'h2', 'h3'
                        ],
                        attributes={
                            'a': ['href', 'title'],
                            'abbr': ['title'],
                            'acronym': ['title'],
                            'code': ['class']
                        })


def validate_markdown(value):
    if value is None:
        return
    html = markdown.markdown(value)
    bleached_html = sanitize_html(html)
    if html != bleached_html:
        diff = io.StringIO()
        diff.writelines(difflib.ndiff(html, bleached_html))
        raise ValidationError('Markdown not sanitized: {}'.format(diff.getvalue()))


class MarkdownField(models.TextField):
    description = "Sanitized Markdown"
    default_validators = [validate_markdown]

    def to_python(self, value):
        validate_markdown(value)
        return value
