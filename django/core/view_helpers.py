from django.views.generic import TemplateView
from django.conf.urls import url
import os

import logging

logger = logging.getLogger(__name__)


def create_edit_routes(url_prefix: str, lookup_field: str, lookup_regex: str, app_name: str):
    base_url = r'{base_url}/(?P<{lookup_field}>{lookup_regex})/'.format(base_url=url_prefix, lookup_field=lookup_field,
                                                                        lookup_regex=lookup_regex)
    update_form_url = base_url + 'update/'
    create_form_url = url_prefix + '/create/'
    template_name = os.path.join(app_name, url_prefix, 'create_or_update.jinja')
    return [
        url(update_form_url, TemplateView.as_view(template_name=template_name),
            name='{url_prefix}-update'.format(url_prefix=url_prefix)),
        url(create_form_url, TemplateView.as_view(template_name=template_name),
            name='{url_prefix}-create'.format(url_prefix=url_prefix))
    ]
