from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from typing import Optional

import logging

logger = logging.getLogger(__name__)


class EditableSerializerMixin(serializers.Serializer):
    editable = serializers.SerializerMethodField(help_text=_('Whether or not entity is editable by the current user'))

    def get_editable(self, obj):
        # logger.debug(self.context)
        request = self.context.get('request')
        if request is None:
            return False

        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        return request.user.has_perm("{}.change_{}".format(app_label, model_name), obj)


def save_tags(instance, tags):
    if not tags.is_valid():
        raise serializers.ValidationError(tags.errors)
    db_tags = tags.save()
    instance.tags.clear()
    instance.tags.add(*db_tags)
