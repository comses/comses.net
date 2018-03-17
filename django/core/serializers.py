import logging

from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from markupfield.fields import Markup
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from taggit.models import Tag

from .models import Event, Job, Institution

logger = logging.getLogger(__name__)

YMD_DATETIME_FORMAT = '%Y-%m-%d'
PUBLISH_DATE_FORMAT = '%b %d, %Y'
FULL_DATE_FORMAT = '%A, %B %d, %Y'


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
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user):
        full_name = user.get_full_name()
        if full_name:
            return full_name
        return user.username

    class Meta:
        model = User
        fields = ('full_name', 'profile_url')


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


class EventSerializer(serializers.ModelSerializer):
    submitter = LinkedUserSerializer(read_only=True, help_text=_('User that created the event'), label='Submitter')
    absolute_url = serializers.URLField(source='get_absolute_url',
                                        read_only=True, help_text=_('URL to the detail page of the event'))
    date_created = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_modified = serializers.DateTimeField(format='%c', read_only=True)
    description = MarkdownField()

    tags = TagSerializer(many=True, label='Tags')

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    def validate(self, attrs):
        date_created = attrs.get('date_created', timezone.now())
        early_registration_deadline = attrs.get('early_registration_deadline')
        submission_deadline = attrs.get('submission_deadline')
        start_date = attrs['start_date']
        end_date = attrs.get('end_date')

        dates = [date_created]
        if early_registration_deadline:
            dates.append(early_registration_deadline)
        if submission_deadline:
            dates.append(submission_deadline)
        dates.append(start_date)
        if end_date:
            dates.append(end_date)

        msgs = []
        if early_registration_deadline and date_created > early_registration_deadline:
            msgs.append('early registration deadline must be after time event is registered')

        if early_registration_deadline and submission_deadline and early_registration_deadline >= submission_deadline:
            msgs.append('early registration deadline must be strictly before submission deadline')

        if submission_deadline and submission_deadline > start_date:
            msgs.append('submission deadline must be before start date')

        if end_date and start_date >= end_date:
            msgs.append('start date must be strictly before end date')

        if msgs:
            raise ValidationError('.'.join(s.capitalize() for s in msgs))

        return attrs

    class Meta:
        model = Event
        fields = '__all__'


class EventCalendarSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(source='start_date')
    end = serializers.DateTimeField(source='end_date')

    class Meta:
        model = Event
        fields = ('title', 'start', 'end',)


class JobSerializer(serializers.ModelSerializer):
    submitter = LinkedUserSerializer(read_only=True, help_text=_('User that created the job description'),
                                     label='Submitter')
    absolute_url = serializers.URLField(
        source='get_absolute_url',
        read_only=True,
        help_text=_('URL to the detail page of the job'))

    date_created = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    description = MarkdownField()
    last_modified = serializers.DateTimeField(format='%c', read_only=True)
    application_deadline = serializers.DateField(allow_null=True, input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', 'iso-8601'])
    formatted_application_deadline = serializers.DateField(source='application_deadline', read_only=True,
                                                           format=PUBLISH_DATE_FORMAT)
    tags = TagSerializer(many=True, label='Tags')

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Job
        fields = ('id', 'title', 'submitter', 'date_created', 'last_modified', 'application_deadline',
                  'formatted_application_deadline', 'description', 'summary', 'absolute_url', 'tags', 'external_url',)


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ('url', 'name',)
