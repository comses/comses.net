import logging

from rest_framework import serializers

from core.models import Institution, MemberProfile
from core.serializers import TagSerializer, MarkdownField
from library.models import Codebase
from library.serializers import RelatedCodebaseSerializer

from .models import (FeaturedContentItem, UserMessage)

logger = logging.getLogger(__name__)


class FeaturedContentItemSerializer(serializers.ModelSerializer):
    image = serializers.SlugRelatedField(read_only=True, slug_field='file')

    class Meta:
        model = FeaturedContentItem
        fields = ('image', 'caption', 'title',)


class UserMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMessage
        field = ('message', 'user')


class MemberProfileSerializer(serializers.ModelSerializer):
    """
    FIXME: References library.Codebase so
    """
    # User fields
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True, format='%c')
    family_name = serializers.CharField(source='user.last_name')
    full_name = serializers.SerializerMethodField(source='user.full_name')
    given_name = serializers.CharField(source='user.first_name')
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email')

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
    tags = TagSerializer(many=True)
    profile_url = serializers.URLField(source='get_absolute_url', read_only=True)
    bio = MarkdownField()
    research_interests = MarkdownField()

    def get_avatar(self, instance):
        request = self.context.get('request')
        if request and request.accepted_media_type != 'text/html':
            return instance.picture.get_rendition('fill-150x150').url if instance.picture else None
        return instance.picture

    def get_codebases(self, instance):
        # FIXME: use django-filter for sort order
        request = self.context.get('request')
        # FIXME: suffers from n + 1 queries
        codebases = Codebase.objects.contributed_by(user=instance.user).accessible(user=request.user)\
            .order_by('-last_published_on')
        return RelatedCodebaseSerializer(codebases, read_only=True, many=True).data

    def get_full_name(self, instance):
        full_name = instance.user.get_full_name()
        if not full_name:
            full_name = instance.user.username
        return full_name

    def update(self, instance, validated_data):
        raw_tags = TagSerializer(many=True, data=validated_data.pop('tags'))
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
        self.save_tags(instance, raw_tags)
        return obj

    @staticmethod
    def save_tags(instance, tags):
        if not tags.is_valid():
            raise serializers.ValidationError(tags.errors)
        db_tags = tags.save()
        instance.tags.clear()
        instance.tags.add(*db_tags)
        instance.save()

    class Meta:
        model = MemberProfile
        fields = (
            # User
            'date_joined', 'family_name', 'full_name', 'given_name', 'profile_url',
            'username', 'email',
            # Follower
            'follower_count', 'following_count',
            'codebases',
            # institution
            'institution_name', 'institution_url',
            # MemberProfile
            'avatar', 'bio', 'degrees', 'full_member', 'tags', 'orcid_url', 'github_url',
            'personal_url', 'professional_url', 'profile_url', 'research_interests')
