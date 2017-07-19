import logging

from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from core.serializers import (YMD_DATETIME_FORMAT, PUBLISH_DATE_FORMAT, LinkedUserSerializer, create, update,
                              TagSerializer)
from .models import CodebaseContributor, Codebase, CodebaseRelease, Contributor, License

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):

    class Meta:
        model = License
        fields = '__all__'


class ContributorSerializer(serializers.ModelSerializer):
    user = LinkedUserSerializer()
    affiliations_list = TagSerializer(source='affiliations', many=True)

    class Meta:
        model = Contributor
        fields = ('given_name', 'middle_name', 'family_name', 'name', 'email', 'user', 'type', 'affiliations_list')


class CodebaseContributorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='contributor.name', read_only=True)
    family_name = serializers.CharField(source='contributor.family_name')
    middle_name = serializers.CharField(source='contributor.middle_name')
    given_name = serializers.CharField(source='contributor.given_name')
    type = serializers.ChoiceField(source='contributor.type', choices=['person', 'organization'])
    username = serializers.CharField(source='contributor.user.username', read_only=True)
    affiliations = serializers.CharField(source='contributor.formatted_affiliations', read_only=True)
    affiliations_list = TagSerializer(source='contributor.affiliations', many=True)
    profile_url = serializers.SerializerMethodField()

    def get_profile_url(self, instance):
        user = instance.contributor.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            # FIXME: replace with reverse('core:search', ...)
            return '/search?{0}'.format(urlencode({'person': instance.contributor.name}))

    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class RelatedCodebaseSerializer(serializers.ModelSerializer):
    """
    Sparse codebase serializer
    """
    all_contributors = CodebaseContributorSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    last_published_on = serializers.DateTimeField(read_only=True, format=PUBLISH_DATE_FORMAT)
    summarized_description = serializers.CharField(read_only=True)
    featured_image = serializers.ReadOnlyField(source='get_featured_image')

    class Meta:
        model = Codebase
        fields = ('featured_image', 'all_contributors', 'tags', 'title', 'last_published_on', 'identifier',
                  'summarized_description')


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    citation_text = serializers.ReadOnlyField()
    codebase = RelatedCodebaseSerializer(read_only=True)
    codebase_contributors = CodebaseContributorSerializer(many=True)
    date_created = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    license = LicenseSerializer()
    os_display = serializers.CharField(source='get_os_display')
    platform_tags = TagSerializer(many=True)
    programming_languages = TagSerializer(many=True)
    submitter = LinkedUserSerializer(label='Submitter')

    class Meta:
        model = CodebaseRelease
        fields = ('absolute_url', 'citation_text', 'codebase_contributors', 'date_created', 'dependencies',
                  'description', 'documentation', 'doi', 'download_count', 'embargo_end_date', 'first_published_at',
                  'last_modified', 'last_published_on', 'license', 'os', 'os_display', 'peer_reviewed', 'platform_tags',
                  'programming_languages', 'submitted_package', 'submitter', 'version_number', 'codebase')


class CodebaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True)
    all_contributors = CodebaseContributorSerializer(many=True, read_only=True)
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
                  'submitter', 'summarized_description', 'tags', 'description', 'title', 'doi', 'identifier',)
