from django.views.generic import TemplateView
from django.conf.urls import url
import os

import logging

logger = logging.getLogger(__name__)


def create_edit_routes(base_name: str, prefix: str, lookup_field: str, lookup_regex: str, app_name: str):
    base_url = r'{prefix}/(?P<{lookup_field}>{lookup_regex})/'.format(prefix=prefix, lookup_field=lookup_field,
                                                                        lookup_regex=lookup_regex)
    update_form_url = base_url + 'update/'
    create_form_url = prefix + '/create/'
    template_name = os.path.join(app_name, prefix, 'create_or_update.jinja')
    return [
        url(update_form_url, TemplateView.as_view(template_name=template_name),
            name='{base_name}-update'.format(base_name=base_name)),
        url(create_form_url, TemplateView.as_view(template_name=template_name),
            name='{base_name}-create'.format(base_name=base_name))
    ]
