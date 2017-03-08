from django.views.generic import TemplateView
from django.conf.urls import url
import os
from django.contrib.auth.decorators import login_required
from guardian.decorators import permission_required_or_403

import logging

logger = logging.getLogger(__name__)


def create_edit_routes(prefix: str, model, lookup_field: str, lookup_regex: str):
    base_url = r'{prefix}/(?P<{lookup_field}>{lookup_regex})/'.format(prefix=prefix, lookup_field=lookup_field,
                                                                        lookup_regex=lookup_regex)
    update_form_url = base_url + 'update/'
    create_form_url = prefix + '/create/'

    app_name = model._meta.app_label
    base_name = model._meta.object_name.lower()
    template_name = os.path.join(app_name, prefix, 'create_or_update.jinja')

    perm = app_name + '.change_' + base_name

    create_view = login_required()(TemplateView.as_view(template_name=template_name))
    update_view = permission_required_or_403(perm, (model, lookup_field, lookup_field))(
        TemplateView.as_view(template_name=template_name))

    return [
        url(update_form_url, create_view,
            name='{base_name}-update'.format(base_name=base_name)),
        url(create_form_url, update_view,
            name='{base_name}-create'.format(base_name=base_name))
    ]
