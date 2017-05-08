from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from taggit.models import Tag

from core.serializers import save_tags, PUBLISH_DATE_FORMAT
from .models import Event, Job, FeaturedContentItem, MemberProfile


class LinkedUserSerializer(serializers.ModelSerializer):
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('username', 'full_name', 'profile_url')


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
    # Add read only properties without defaults
    user = context['request'].user
    validated_data['submitter_id'] = user.id
    # Relate with other many to many relations
    obj = model_cls.objects.create(**validated_data)
    save_tags(obj, tags)
    return obj


def update(serializer_update, instance, validated_data):
    tags = TagSerializer(many=True, data=validated_data.pop('tags'))
    obj = serializer_update(instance, validated_data)
    save_tags(obj, tags)
    return obj


class EventSerializer(serializers.ModelSerializer):
    submitter = LinkedUserSerializer(read_only=True, help_text=_('User that created the event'), label='Submitter')
    absolute_url = serializers.URLField(source='get_absolute_url',
                                        read_only=True, help_text=_('URL to the detail page of the event'))
    date_created = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_modified = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)

    tags = TagSerializer(many=True, label='Tags')

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

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
    last_modified = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    tags = TagSerializer(many=True, label='Tags')

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Job
        fields = ('id', 'title', 'submitter', 'date_created', 'last_modified',
                  'description', 'summary', 'absolute_url', 'tags')


class FeaturedContentItemSerializer(serializers.ModelSerializer):
    image = serializers.SlugRelatedField(read_only=True, slug_field='file')

    class Meta:
        model = FeaturedContentItem
        fields = ('image', 'caption', 'title',)


class MemberProfileSerializer(serializers.ModelSerializer):
    full_member = serializers.BooleanField(read_only=True)

    class Meta:
        model = MemberProfile
        fields = ('__all__')


class UserSerializer(serializers.ModelSerializer):
    member_profile = MemberProfileSerializer(read_only=True, allow_null=True)
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    username = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True, format='%c')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'is_superuser', 'is_staff', 'member_profile', 'get_full_name',
                  'profile_url', 'date_joined')
