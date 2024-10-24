from allauth.socialaccount.adapter import get_adapter
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib import messages
from django.forms.widgets import CheckboxInput
from django.template import defaultfilters
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.text import slugify
from django.utils.timezone import get_current_timezone
from django.utils.timesince import timeuntil, timesince
from jinja2 import Environment
from markupsafe import Markup

from hcaptcha_field import hCaptchaField

import re
import json
import logging
from datetime import datetime
from urllib.parse import parse_qsl

from core.fields import render_sanitized_markdown
from core.serializers import FULL_DATE_FORMAT, FULL_DATETIME_FORMAT


logger = logging.getLogger(__name__)


def get_download_request_metadata(user):
    """FIXME: this doesn't quite fit here, too specialized, possibly get_context_data()?"""
    EMPTY_DOWNLOAD_REQUEST_METADATA = {
        "authenticated": False,
        "affiliation": {},
        "industry": "",
        "id": None,
    }
    # start with base download request metadata
    metadata = EMPTY_DOWNLOAD_REQUEST_METADATA
    if user is not None and user.is_authenticated:
        metadata = user.member_profile.get_download_request_metadata()
    return json.dumps(metadata)


def jinja_url(viewname, *args, **kwargs):
    return reverse(viewname, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    constants = {
        "DISCOURSE_BASE_URL": settings.DISCOURSE_BASE_URL,
        "DEBUG": settings.DEBUG,
        "RELEASE_VERSION": settings.RELEASE_VERSION,
        "SENTRY_DSN": settings.SENTRY_DSN,
        "DEPLOY_ENVIRONMENT": settings.DEPLOY_ENVIRONMENT,
    }
    env.globals.update(
        {
            "static": static,
            "url": jinja_url,
            "slugify": slugify,
            "constants": constants,
            "build_absolute_uri": build_absolute_uri,
            "cookielaw": cookielaw,
            "now": now,
            "generate_search_form_inputs": generate_search_form_inputs,
            "should_enable_discourse": should_enable_discourse,
            "is_production": is_production,
            "provider_login_url": provider_login_url,
            "provider_display_name": provider_display_name,
            "get_choices_display": get_choices_display,
            "get_download_request_metadata": get_download_request_metadata,
            "markdown": markdown,
            "add_field_css": add_field_css,
            "format_date_str": format_date_str,
            "format_date": format_date,
            "format_datetime_str": format_datetime_str,
            "format_datetime": format_datetime,
            "timeuntil": _timeuntil,
            "timesince": _timesince,
            "to_json": to_json,
            "is_checkbox": is_checkbox,
            "is_hcaptcha": is_hcaptcha,
            "get_messages": messages.get_messages,
            "strip_url_scheme": strip_url_scheme,
        }
    )
    return env


def build_absolute_uri(relative_url):
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    absolute_url = "{}://{}{}".format(protocol, domain, relative_url)
    return absolute_url


def cookielaw(request):
    if request.COOKIES.get("cookielaw_accepted", False):
        return ""
    return render_to_string("cookielaw/cookielaw.jinja", request=request)


def now(format_string):
    """
    Simulates the Django https://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
    default templatetag
    Usage: {{ now('Y') }}
    """
    tzinfo = get_current_timezone() if settings.USE_TZ else None
    return defaultfilters.date(datetime.now(tz=tzinfo), format_string)


def to_camel_case(snake_str):
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_keys_to_camel_case(d: list):
    return [(to_camel_case(k), v) for k, v in d]


def generate_search_form_inputs(query_params):
    """
    Generate hidden input fields for the search form based on incoming query parameters.
    Args:
        query_params (str): The query parameters to be used for generating the hidden inputs.
    Returns:
        list: A list of tuples representing the hidden input fields.
    """
    search_parameters = {}
    if query_params:
        # parse_qsl handles splitting and unquoting key-value pairs and generates a list of tuples
        # do not include the actual query in the query parameters
        incoming_query_params = [
            pair for pair in parse_qsl(query_params) if pair[0] != "query"
        ]
        search_parameters.update(convert_keys_to_camel_case(incoming_query_params))

    logger.debug("search parameters: %s", search_parameters)
    return search_parameters.items()


def should_enable_discourse(is_public: bool):
    """
    Returns True if we are not in DEBUG mode and the detail object (wagtail Page or django
    Model, e.g., Codebase/CodebaseRelease/Event/Job) is public.
    """
    return is_public and not settings.DEPLOY_ENVIRONMENT.is_development


def is_production():
    return settings.DEPLOY_ENVIRONMENT.is_production and not settings.DEBUG


def provider_login_url(request, provider_id, **kwargs):
    provider = get_adapter().get_provider(request, provider_id)
    next_url = request.GET.get("next", None)
    if next_url:
        kwargs["next"] = next_url
    return provider.get_login_url(request, **kwargs)


def provider_display_name(provider_name):
    if provider_name == "github":
        return "GitHub"
    elif provider_name == "orcid":
        return "ORCID"
    else:
        return provider_name


def get_choices_display(selected_choice, choices):
    """
    Takes a Choices enum string key alongside its parent Choices Enum class and returns the display label for that
    particular selected_choice.
    """
    return choices(selected_choice).label


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
        css_classes += " is-invalid"
    css_classes = field.css_classes(css_classes)
    deduped_css_classes = " ".join(set(css_classes.split(" ")))
    return field.as_widget(attrs={"class": deduped_css_classes})


def format_datetime_str(datetime_str, format_str=FULL_DATETIME_FORMAT):
    if datetime_str is None:
        return None
    datetime_obj = parse_datetime(datetime_str)
    return format_datetime(datetime_obj, format_str)


def format_datetime(datetime_obj, format_str=FULL_DATETIME_FORMAT):
    if datetime_obj is None:
        return None
    return datetime_obj.strftime(format_str)


def format_date_str(date_str, format_str=FULL_DATE_FORMAT):
    if date_str is None:
        return None
    date_obj = parse_date(date_str) or parse_datetime(date_str)
    return format_date(date_obj, format_str)


def format_date(date_obj, format_str=FULL_DATE_FORMAT):
    if date_obj is None:
        return None
    return date_obj.strftime(format_str)


def _timesince(date_str, depth=1):
    if date_str is None:
        return None
    date_obj = parse_date(date_str) or parse_datetime(date_str)
    return timesince(date_obj, depth=depth) if date_obj else None


def _timeuntil(date_str, depth=1):
    if date_str is None:
        return None
    date_obj = parse_date(date_str) or parse_datetime(date_str)
    return timeuntil(date_obj, depth=depth) if date_obj else None


def to_json(value):
    return json.dumps(value)


def strip_url_scheme(url):
    return re.sub(r"^https?:\/\/", "", url) if url else None


# # http://stackoverflow.com/questions/6453652/how-to-add-the-current-query-string-to-an-url-in-a-django-template
# @register.simple_tag
# def query_transform(request, **kwargs):
#     updated = request.GET.copy()
#     for k, v in kwargs.iteritems():
#         updated[k] = v
#
#     return updated.urlencode()
