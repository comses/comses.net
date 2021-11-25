from allauth.socialaccount import providers
from datetime import datetime
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib import messages
from django.forms.widgets import CheckboxInput
from django.template import defaultfilters
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone
from jinja2 import Environment, Markup

from hcaptcha_field import hCaptchaField
from typing import Optional

import json
import logging


from core.fields import render_sanitized_markdown
from core.serializers import FULL_DATE_FORMAT


logger = logging.getLogger(__name__)

def jinja_url(viewname, *args, **kwargs):
    return reverse(viewname, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    constants = {
        'DISCOURSE_BASE_URL': settings.DISCOURSE_BASE_URL,
        'DEBUG': settings.DEBUG,
        'RELEASE_VERSION': settings.RELEASE_VERSION,
        'SENTRY_DSN': settings.SENTRY_DSN,
        'DEPLOY_ENVIRONMENT': settings.DEPLOY_ENVIRONMENT,
    }
    env.globals.update({
        'static': static,
        'url': jinja_url,
        'constants': constants,
        'build_absolute_uri': build_absolute_uri,
        'cookielaw': cookielaw,
        'now': now,
        'should_enable_discourse': should_enable_discourse,
        'is_production': is_production,
        'provider_login_url': provider_login_url,
        'get_choices_display': get_choices_display,
        'markdown': markdown,
        'add_field_css': add_field_css,
        'format_datetime_str': format_datetime_str,
        'format_datetime': format_datetime,
        'to_json': to_json,
        'is_checkbox': is_checkbox,
        'is_hcaptcha': is_hcaptcha,
        'get_messages': messages.get_messages,
    })
    return env

def build_absolute_uri(relative_url):
    domain = Site.objects.get_current().domain
    protocol = 'https' if settings.SECURE_SSL_REDIRECT else 'http'
    absolute_url = '{}://{}{}'.format(protocol, domain, relative_url)
    return absolute_url


def cookielaw(request):
    if request.COOKIES.get('cookielaw_accepted', False):
        return ''
    return render_to_string('cookielaw/cookielaw.jinja', request=request)


def now(format_string):
    """
    Simulates the Django https://docs.djangoproject.com/en/dev/ref/templates/builtins/#now default templatetag
    Usage: {{ now('Y') }}
    """
    tzinfo = get_current_timezone() if settings.USE_TZ else None
    return defaultfilters.date(datetime.now(tz=tzinfo), format_string)


def should_enable_discourse(is_public: bool):
    """
    Returns True if we are not in DEBUG mode and the detail object (the wagtail Page or django Model, e.g.,
    Codebase/CodebaseRelease/Event/Job) is public. If there is no 'live' attribute, default to True as it is public by
    default.
    """
    return is_public and not settings.DEPLOY_ENVIRONMENT.is_development()


def is_production():
    return settings.DEPLOY_ENVIRONMENT.is_production() and not settings.DEBUG


def provider_login_url(request, provider_id, **kwargs):
    provider = providers.registry.by_id(provider_id, request)
    next_url = request.GET.get('next', None)
    if next_url:
        kwargs['next'] = next_url
    return provider.get_login_url(request, **kwargs)


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


def is_checkbox(bound_field):
    return isinstance(bound_field.field.widget, CheckboxInput)

def is_hcaptcha(bound_field):
    return isinstance(bound_field.field, hCaptchaField)


def markdown(text: str):
    """
    Returns a sanitized HTML string representing the rendered version of the incoming Markdown text.
    :param text: string markdown source text to be converted
    :return: sanitized html string, explicitly marked as safe via jinja2.Markup
    """
    return Markup(render_sanitized_markdown(text))


def add_field_css(field, css_classes: str):
    if field.errors:
        css_classes += ' is-invalid'
    css_classes = field.css_classes(css_classes)
    deduped_css_classes = ' '.join(set(css_classes.split(' ')))
    return field.as_widget(attrs={'class': deduped_css_classes})


def format_datetime_str(text: Optional[str], format_string=FULL_DATE_FORMAT):
    if text is None:
        return None
    d = parse_datetime(text)
    return format_datetime(d, format_string)


def format_datetime(date_obj, format_string=FULL_DATE_FORMAT):
    if date_obj is None:
        return None
    return date_obj.strftime(format_string)


def to_json(value):
    return json.dumps(value)

# # http://stackoverflow.com/questions/6453652/how-to-add-the-current-query-string-to-an-url-in-a-django-template
# @register.simple_tag
# def query_transform(request, **kwargs):
#     updated = request.GET.copy()
#     for k, v in kwargs.iteritems():
#         updated[k] = v
#
#     return updated.urlencode()
