import logging

from django.contrib.auth.models import User
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from core.serializers import (YMD_DATETIME_FORMAT, PUBLISH_DATE_FORMAT, LinkedUserSerializer, create, update,
                              save_tags,
                              TagSerializer)
from .models import ReleaseContributor, Codebase, CodebaseRelease, Contributor, License
from home.common_serializers import RelatedMemberProfileSerializer

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        license = License.objects.filter(name=validated_data['name']).first()
        if license is not None:
            if validated_data['url'] != license.url:
                license.url = validated_data['url']
                license.save()
        else:
            license = super().create(validated_data)

        return license

    class Meta:
        model = License
        fields = ('name', 'url',)


class ContributorSerializer(serializers.ModelSerializer):
    # Need an ID for Vue-Multiselect
    id = serializers.IntegerField(read_only=True)
    user = RelatedMemberProfileSerializer(required=False, allow_null=True)
    affiliations = TagSerializer(many=True)

    def _create_or_update(self, validated_data):
        affiliations_serializer = TagSerializer(many=True, data=validated_data.pop('affiliations'))
        raw_user = validated_data.pop('user')
        if raw_user:
            user = User.objects.get(username=validated_data.pop('user')['username'])
        else:
            user = None
        validated_data['user_id'] = user.id if user else None
        return affiliations_serializer, user

    def create(self, validated_data):
        affiliations_list_serializer, user = self._create_or_update(validated_data)
        instance = super().create(validated_data)
        save_tags(instance, affiliations_list_serializer, 'affiliations')
        instance.save()
        return instance

    class Meta:
        model = Contributor
        fields = ('id', 'given_name', 'middle_name', 'family_name', 'name', 'email', 'user', 'type', 'affiliations')


class ReleaseContributorSerializer(serializers.ModelSerializer):
    contributor = ContributorSerializer()
    profile_url = serializers.SerializerMethodField()

    def get_profile_url(self, instance):
        user = instance.contributor.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            # FIXME: replace with reverse('core:search', ...)
            return '/search?{0}'.format(urlencode({'person': instance.contributor.name}))

    def create(self, validated_data):
        contributor_serializer = ContributorSerializer()
        contributor_serializer._errors = {}
        contributor_serializer._validated_data = validated_data.pop('contributor')
        contributor = contributor_serializer.save()

        validated_data['release_id'] = self.context['release_id']
        validated_data['contributor_id'] = contributor.id
        instance = super().create(validated_data)
        return instance

    class Meta:
        model = ReleaseContributor
        fields = ('contributor', 'profile_url',
                  'include_in_citation', 'is_maintainer', 'is_rights_holder',
                  'role', 'index',)


class RelatedCodebaseSerializer(serializers.ModelSerializer):
    """
    Sparse codebase serializer
    """
    all_contributors = ReleaseContributorSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    last_published_on = serializers.DateTimeField(read_only=True, format=PUBLISH_DATE_FORMAT)
    summarized_description = serializers.CharField(read_only=True)
    featured_image = serializers.ReadOnlyField(source='get_featured_image')

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = ('featured_image', 'all_contributors', 'tags', 'title', 'last_published_on', 'identifier',
                  'summarized_description', 'description', 'live', 'repository_url',)


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    citation_text = serializers.ReadOnlyField()
    codebase = RelatedCodebaseSerializer(read_only=True)
    release_contributors = ReleaseContributorSerializer(source='codebase_contributors', many=True)
    date_created = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    license = LicenseSerializer()
    os_display = serializers.CharField(read_only=True, source='get_os_display')
    platforms = TagSerializer(many=True, source='platform_tags')
    programming_languages = TagSerializer(many=True)
    submitter = LinkedUserSerializer(read_only=True, label='Submitter')

    def update(self, instance, validated_data):
        programming_languages = TagSerializer(many=True, data=validated_data.pop('programming_languages'))
        platform_tags = TagSerializer(many=True, data=validated_data.pop('platform_tags'))
        release_contributors = ReleaseContributorSerializer(many=True, data=self.initial_data['release_contributors'],
                                                            context={'release_id': instance.id})
        release_contributors._validated_data = validated_data.pop('codebase_contributors')
        release_contributors._errors = {}

        license_serializer = LicenseSerializer(data=validated_data.pop('license'))
        license_serializer.is_valid(raise_exception=True)
        license = license_serializer.save()

        save_tags(instance, programming_languages, 'programming_languages')
        save_tags(instance, platform_tags, 'platform_tags')
        self.save_release_contributors(instance, release_contributors)

        instance = super().update(instance, validated_data)

        instance.license = license
        instance.save()

        return instance

    def save_release_contributors(self, instance: CodebaseRelease,
                                  release_contributors_serializer: ReleaseContributorSerializer):
        release_contributors_serializer.is_valid(raise_exception=True)
        release_contributors = release_contributors_serializer.save()

        # Old contributors are not deleted from the database
        instance.contributors.clear()
        instance.codebase_contributors = release_contributors

    class Meta:
        model = CodebaseRelease
        fields = ('absolute_url', 'citation_text', 'release_contributors', 'date_created', 'dependencies',
                  'description', 'documentation', 'doi', 'download_count', 'embargo_end_date', 'first_published_at',
                  'last_modified', 'last_published_on', 'license', 'os', 'os_display', 'peer_reviewed', 'platforms',
                  'programming_languages', 'submitted_package', 'submitter', 'version_number', 'codebase', 'identifier',
                  'id',)


class CodebaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True)
    all_contributors = ReleaseContributorSerializer(many=True, read_only=True)
    date_created = serializers.DateTimeField(read_only=True)
    download_count = serializers.IntegerField(read_only=True)
    featured_image = serializers.ReadOnlyField(source='get_featured_image')
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    latest_version_number = serializers.ReadOnlyField(source='latest_version.version_number')
    current_version = CodebaseReleaseSerializer(read_only=True)
    releases = CodebaseReleaseSerializer(read_only=True, many=True)
    submitter = LinkedUserSerializer(read_only=True)
    summarized_description = serializers.CharField(read_only=True)
    tags = TagSerializer(many=True)

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = ('absolute_url', 'all_contributors', 'date_created', 'download_count', 'featured_image',
                  'first_published_at', 'last_published_on', 'latest_version_number', 'current_version', 'releases',
                  'submitter', 'summarized_description', 'tags', 'description', 'title', 'doi', 'identifier', 'id',)
