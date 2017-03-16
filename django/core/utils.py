import markdown
import bleach

ALLOWED_TAGS = bleach.ALLOWED_TAGS + ['p', 'h1', 'h2', 'h3', 'pre', 'br']


def markdown_to_sanitized_html(md: str):
    html = markdown.markdown(md)
    sanitized_html = bleach.clean(bleach.linkify(html), tags=ALLOWED_TAGS)
    return sanitized_html
