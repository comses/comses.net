import logging
from datetime import datetime, timezone

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.models import Institution, MemberProfile, Event, Job
from core.serializers import (PUBLISH_DATE_FORMAT, LinkedUserSerializer, TagSerializer, create, update)
from library.models import Codebase
from library.serializers import RelatedCodebaseSerializer
from .models import (FeaturedContentItem, UserMessage)

logger = logging.getLogger(__name__)


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

    def validate(self, attrs):
        date_created = attrs.get('date_created', datetime.now(timezone.utc))
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


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ('url', 'name',)


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
    # FIXME: move to core to live with core.models.MemberProfile
    # User fields
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True, format='%c')
    family_name = serializers.CharField(source='user.last_name')
    full_name = serializers.SerializerMethodField(source='user.full_name')
    given_name = serializers.CharField(source='user.first_name')
    username = serializers.CharField(source='user.username', read_only=True)

    # Followers
    follower_count = serializers.ReadOnlyField(source='user.following.count')
    following_count = serializers.ReadOnlyField(source='user.followers.count')

    codebases = serializers.SerializerMethodField()

    # Institution
    institution_name = serializers.CharField()
    institution_url = serializers.URLField()

    # MemberProfile
    avatar = serializers.SerializerMethodField()  # needed to materialize the FK relationship for wagtailimages
    orcid_url = serializers.ReadOnlyField()
    github_url = serializers.ReadOnlyField()
    keywords = TagSerializer(many=True)
    profile_url = serializers.URLField(source='get_absolute_url', read_only=True)

    def get_avatar(self, instance):
        request = self.context.get('request')
        if request and request.accepted_media_type != 'text/html':
            return instance.picture.get_rendition('fill-150x150').url if instance.picture else None
        return instance.picture

    def get_codebases(self, instance):
        # FIXME: use django-filter for sort order
        request = self.context.get('request')

        # This suffers from the n + 1 query problem
        codebases = Codebase.objects.contributed_by(user=instance.user).accessible(user=request.user)\
            .order_by('-last_published_on')
        return RelatedCodebaseSerializer(codebases, read_only=True, many=True).data

    def get_full_name(self, instance):
        full_name = instance.user.get_full_name()
        if not full_name:
            full_name = instance.user.username
        return full_name

    def update(self, instance, validated_data):
        raw_tags = TagSerializer(many=True, data=validated_data.pop('keywords'))
        user = instance.user
        raw_user = validated_data.pop('user')
        user.first_name = raw_user['first_name']
        user.last_name = raw_user['last_name']

        raw_institution = {'name': validated_data.pop('institution_name'),
                           'url': validated_data.pop('institution_url')}
        institution = instance.institution
        if institution:
            institution.name = raw_institution.get('name')
            institution.url = raw_institution.get('url')
            institution.save()
        else:
            institution = Institution.objects.create(**raw_institution)
            instance.institution = institution

        user.save()
        obj = super().update(instance, validated_data)
        self.save_keywords(instance, raw_tags)
        return obj

    @staticmethod
    def save_keywords(instance, tags):
        if not tags.is_valid():
            raise serializers.ValidationError(tags.errors)
        db_tags = tags.save()
        instance.keywords.clear()
        instance.keywords.add(*db_tags)
        instance.save()

    class Meta:
        model = MemberProfile
        fields = (
            # User
            'date_joined', 'family_name', 'full_name', 'given_name', 'profile_url',
            'username',
            # Follower
            'follower_count', 'following_count',
            'codebases',
            # institution
            'institution_name', 'institution_url',
            # MemberProfile
            'avatar', 'bio', 'degrees', 'bio', 'degrees', 'full_member', 'keywords', 'orcid_url', 'github_url',
            'personal_url', 'professional_url', 'profile_url', 'research_interests')


class UserMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMessage
        field = ('message', 'user')
