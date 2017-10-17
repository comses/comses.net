from datetime import datetime
from typing import Optional

from allauth.socialaccount import providers
from django.conf import settings
from django.forms.widgets import CheckboxInput
from django.template import defaultfilters
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone
from django_jinja import library
from jinja2 import Markup
from webpack_loader.templatetags import webpack_loader as wl

from core.serializers import PUBLISH_DATE_FORMAT
from core.summarization import summarize
from core.fields import render_sanitized_markdown


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
def should_enable_discourse(is_public: bool):
    """
    Returns True if we are not in DEBUG mode and the detail object (the wagtail Page or django Model, e.g.,
    Codebase/CodebaseRelease/Event/Job) is public. If there is no 'live' attribute, default to True as it is public by
    default.
    """
    return is_public and not settings.DEBUG

@library.global_function
def is_debug():
    return settings.DEBUG


@library.global_function
def is_production():
    return settings.DEPLOY_ENVIRONMENT.is_production()


@library.global_function
def provider_login_url(request, provider_id, **kwargs):
    provider = providers.registry.by_id(provider_id, request)
    return provider.get_login_url(request, **kwargs)


@library.global_function
def summarize_markdown(md):
    return summarize(md, 2)


@library.global_function
def get_choices_display(selected_choice, choices):
    """
    Takes a model_utils.Choices key entry alongside its parent set of Choices and returns the display value for that
    particular selected_choice. Tries a pair tuple first ("foo", "Display value for foo") and then the triple
    (<numeric_id>, "foo", "Display value for foo")
    """
    try:
        return choices[selected_choice]
    except:
        return choices[getattr(choices, selected_choice)]


@library.filter
def is_checkbox(bound_field):
    return isinstance(bound_field.field.widget, CheckboxInput)


@library.filter
def markdown(text: str):
    """
    Returns a sanitized HTML string representing the rendered version of the incoming Markdown text.
    :param text: string markdown source text to be converted
    :return: sanitized html string, explicitly marked as safe via jinja2.Markup
    """
    return Markup(render_sanitized_markdown(text))


@library.filter
def add_field_css(field, *args):
    css_classes = field.css_classes(*args)
    deduped_css_classes = ' '.join(set(css_classes.split(' ')))
    return field.as_widget(attrs={'class': deduped_css_classes})


@library.filter
def truncate_midnight(text: Optional[str]):
    if text is None:
        return None

    d = parse_datetime(text)
    if d.minute == 0 and d.second == 0 and d.hour == 0:
        return d.strftime(PUBLISH_DATE_FORMAT)
    else:
        return text

# # http://stackoverflow.com/questions/6453652/how-to-add-the-current-query-string-to-an-url-in-a-django-template
# @register.simple_tag
# def query_transform(request, **kwargs):
#     updated = request.GET.copy()
#     for k, v in kwargs.iteritems():
#         updated[k] = v
#
#     return updated.urlencode()
