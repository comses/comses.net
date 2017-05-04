import logging

from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from core.serializer_helpers import YMD_DATETIME_FORMAT
from home import serializers as home_serializers
from .models import CodebaseContributor, Codebase, CodebaseRelease, Contributor

logger = logging.getLogger(__name__)


class ContributorSerializer(serializers.ModelSerializer):
    user = home_serializers.LinkedUserSerializer()

    class Meta:
        model = Contributor
        fields = ('name', 'email', 'user',)


class CodebaseContributorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='contributor.name', read_only=True)
    username = serializers.CharField(source='contributor.user.username', read_only=True)
    affiliations = serializers.CharField(source='contributor.formatted_affiliations', read_only=True)
    profile_url = serializers.SerializerMethodField()

    def get_profile_url(self, instance):
        user = instance.contributor.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            # FIXME: replace with reverse('core:search', ...)
            logger.error("name: %s", instance.contributor.name)
            return '/search?{0}'.format(urlencode({'person': instance.contributor.name}))

    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    first_published_at = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    date_created = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    codebase_contributors = CodebaseContributorSerializer(many=True)
    submitter = home_serializers.LinkedUserSerializer(label='Submitter')
    platforms = home_serializers.TagSerializer(many=True)
    programming_languages = home_serializers.TagSerializer(many=True)

    class Meta:
        model = CodebaseRelease
        fields = ('date_created', 'last_modified', 'peer_reviewed', 'doi', 'description', 'license', 'documentation',
                  'embargo_end_date', 'version_number', 'os', 'platforms', 'programming_languages', 'submitter',
                  'codebase_contributors', 'submitted_package', 'absolute_url', 'first_published_at', 'download_count')


class CodebaseSerializer(serializers.ModelSerializer):
    all_contributors = CodebaseContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(read_only=True, many=True)
    first_published_at = serializers.DateTimeField(read_only=True)
    date_created = serializers.DateTimeField(read_only=True)
    last_published_on = serializers.DateTimeField(read_only=True)
    tags = home_serializers.TagSerializer(many=True)
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True)
    submitter = home_serializers.LinkedUserSerializer(read_only=True)
    latest_version = CodebaseReleaseSerializer(read_only=True)
    download_count = serializers.IntegerField(read_only=True)
    summarized_description = serializers.CharField(read_only=True)
    featured_image = serializers.ReadOnlyField(source='get_featured_image')

    def create(self, validated_data):
        return home_serializers.create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return home_serializers.update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        exclude = ('featured_images',)
