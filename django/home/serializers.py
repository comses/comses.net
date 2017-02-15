from rest_framework import serializers
from taggit.models import Tag
from .models import Event, Job
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from taggit.models import Tag
from wagtail_comses_net.serializer_helpers import EditableSerializerMixin, save_tags


class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


class TagListSerializer(serializers.ListSerializer):
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
    if tags.is_valid(raise_exception=True):
        tags.save()
    # Add read only properties without defaults
    user = context['request'].user
    validated_data['submitter_id'] = user.id
    # Relate with other many to many relations
    obj = model_cls.objects.create(**validated_data)
    save_tags(obj, tags)
    return obj


def update(serializer_update, instance, validated_data):
    tags = TagSerializer(many=True, data=validated_data.pop('tags'))
    if tags.is_valid(raise_exception=True):
        tags.save()
    obj = serializer_update(instance, validated_data)
    save_tags(obj, tags)
    return obj


class EventSerializer(serializers.ModelSerializer, EditableSerializerMixin):
    submitter = CreatorSerializer(read_only=True, help_text=_('User that created the event'))
    url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the job'))
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = TagSerializer(many=True)

    def get_url(self, obj):
        return reverse_lazy('home:event-detail', kwargs={'pk': obj.id})

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Event
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer, EditableSerializerMixin):
    # need nested serializer for submitter
    submitter = CreatorSerializer(read_only=True, help_text=_('User that created the job description'))
    url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the job'))
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = TagSerializer(many=True)

    def get_url(self, obj):
        return reverse_lazy('home:job-detail', kwargs={'pk': obj.id})

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Job
        fields = ('id', 'title', 'submitter', 'date_created', 'description', 'url', 'tags', 'editable')
