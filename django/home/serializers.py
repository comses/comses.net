from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from core.serializers import PUBLISH_DATE_FORMAT, LinkedUserSerializer, TagSerializer, create, update
from library.serializers import CodebaseSerializer
from .models import Event, Job, FeaturedContentItem, MemberProfile, UserMessage


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
    orcid_url = serializers.SerializerMethodField()
    keywords = TagSerializer(many=True)

    def get_orcid_url(self, instance):
        if instance.orcid:
            return 'https://orcid.org/{0}'.format(instance.orcid)
        return ''

    class Meta:
        model = MemberProfile
        fields = ('__all__')


class UserSerializer(serializers.ModelSerializer):
    member_profile = MemberProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    username = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True, format='%c')
# FIXME: consider loading codebases separately in the ViewSet..
    codebases = CodebaseSerializer(read_only=True, many=True)

    def get_full_name(self, instance):
        full_name = instance.get_full_name()
        if not full_name:
            full_name = instance.username
        return full_name

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'is_superuser', 'is_staff', 'member_profile', 'full_name',
                  'profile_url', 'date_joined', 'codebases')


class UserMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMessage
        field = ('message', 'user')
