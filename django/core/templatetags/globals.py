from datetime import datetime
from django.conf import settings
from django.template import defaultfilters
from django.utils.timezone import get_current_timezone
from django_jinja import library
from ..summarization import summarize
from ..utils import markdown_to_sanitized_html

from webpack_loader.templatetags import webpack_loader as wl


@library.global_function
def render_bundle(bundle_name, extension=None, config='DEFAULT', attrs=''):
    return wl.render_bundle(bundle_name, extension, config, attrs)


@library.global_function
def now(format_string):
    """
    Simulates the Django https://docs.djangoproject.com/en/1.10/ref/templates/builtins/#now default templatetag
    Usage: {{ now('Y') }}
    """
    tzinfo = get_current_timezone() if settings.USE_TZ else None
    return defaultfilters.date(datetime.now(tz=tzinfo), format_string)


@library.global_function
def summarize_markdown(md):
    return summarize(md, 2)


@library.global_function
def markdown(md):
    return markdown_to_sanitized_html(md)

# # http://stackoverflow.com/questions/6453652/how-to-add-the-current-query-string-to-an-url-in-a-django-template
# @register.simple_tag
# def query_transform(request, **kwargs):
#     updated = request.GET.copy()
#     for k, v in kwargs.iteritems():
#         updated[k] = v
#
#     return updated.urlencode()
