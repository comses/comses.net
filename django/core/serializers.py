import logging

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from markupfield.fields import Markup
from rest_framework import serializers
from taggit.models import Tag

logger = logging.getLogger(__name__)

YMD_DATETIME_FORMAT = '%Y-%m-%d'
PUBLISH_DATE_FORMAT = '%b %d, %Y'

class TagListSerializer(serializers.ListSerializer):
    """
    FIXME: needs to implement update & create from base class.
    """
    def save(self, **kwargs):
        data_mapping = {item['name']: item for item in self.validated_data}

        # Perform creations and updates.
        tags = []
        for tag_name, data in data_mapping.items():
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)

        return tags


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField()  # disable uniqueness check so TagListSerializer will validate properly

    class Meta:
        model = Tag
        fields = ('name',)
        list_serializer_class = TagListSerializer


def create(model_cls, validated_data, context):
    # Create related many to many
    tags = TagSerializer(many=True, data=validated_data.pop('tags'))
    # Add read only properties without defaults
    user = context['request'].user
    validated_data['submitter_id'] = user.id
    # Relate with other many to many relations
    obj = model_cls.objects.create(**validated_data)
    save_tags(obj, tags)
    obj.save()
    return obj


def update(serializer_update, instance, validated_data):
    tags = TagSerializer(many=True, data=validated_data.pop('tags'))
    instance = serializer_update(instance, validated_data)
    save_tags(instance, tags)
    instance.save()
    return instance


class LinkedUserSerializer(serializers.ModelSerializer):
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('username', 'full_name', 'profile_url')


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


def save_tags(instance, related, attr: str = 'tags'):
    if not related.is_valid():
        raise serializers.ValidationError(related.errors)
    db_tags = related.save()
    getattr(instance, attr).clear()
    getattr(instance, attr).add(*db_tags)


class MarkdownField(serializers.Field):

    def to_representation(self, obj):
        if isinstance(obj, Markup):
            return obj.raw
        return obj

    def to_internal_value(self, data):
        return data
