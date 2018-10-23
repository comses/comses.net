from distutils.util import strtobool

from dateutil import parser
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.utils import timezone

from core.templatetags.globals import markdown

import logging

logger = logging.getLogger(__name__)


def parse_datetime(datetime_str: str):
    """
    Parses a datetime string with optional timezone encoding and returns a timezone aware datetime.
    If an empty string is passed in, returns None. If an invalid datetime string is given a ValueError will be raised
    http://dateutil.readthedocs.io/en/stable/parser.html
    """
    if datetime_str:
        dt = parser.parse(datetime_str)
        if dt.tzinfo is None:
            return timezone.make_aware(dt)
        return dt
    return None


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        print("Invalid response ", response_as_bool, ". Please confirm with yes (y) or no (n).")
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)
    return True


def create_markdown_email(subject: str, to, template_name: str=None, context: dict=None, body=None, from_email: str=settings.DEFAULT_FROM_EMAIL,
                          **kwargs):
    if all([template_name, context]):
        # override body if a template name and context were given to us
        try:
            template = get_template(template_name)
            body = template.render(context=context)
        except TemplateDoesNotExist:
            logger.error("couldn't find template %s", template_name)
        except TemplateSyntaxError:
            logger.error("invalid template %s", template_name)
    if body:
        email = EmailMultiAlternatives(subject=subject, body=body, to=to, from_email=from_email, **kwargs)
        email.attach_alternative(markdown(body), 'text/html')
        return email
    else:
        raise ValueError("Ignoring request to create a markdown email with no content")


def send_markdown_email(subject: str, body: str, to, from_email=settings.DEFAULT_FROM_EMAIL, **kwargs):
    create_markdown_email(subject, body, to, from_email, **kwargs).send()
