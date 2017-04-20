from textwrap import shorten

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from home import serializers as home_serializers
from .models import CodebaseContributor, Codebase, CodebaseRelease, Contributor


class ContributorSerializer(serializers.ModelSerializer):
    user = home_serializers.CreatorSerializer()

    class Meta:
        model = Contributor
        fields = ('name', 'email', 'user',)


class CodebaseContributorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='contributor.name', read_only=True)
    username = serializers.CharField(source='contributor.user.username', read_only=True)
    affiliations = serializers.CharField(source='contributor.formatted_affiliations', read_only=True)
    profile_url = serializers.CharField(source='contributor.user.member_profile.get_absolute_url', read_only=True)

    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    codebase_contributors = CodebaseContributorSerializer(many=True)
    submitter = home_serializers.UserSerializer(label='Submitter')
    platforms = home_serializers.TagSerializer(many=True)
    programming_languages = home_serializers.TagSerializer(many=True)

    class Meta:
        model = CodebaseRelease
        fields = ('date_created', 'last_modified', 'peer_reviewed', 'doi', 'description', 'license', 'documentation',
                  'embargo_end_date', 'version_number', 'os', 'platforms', 'programming_languages', 'submitter',
                  'codebase_contributors', 'submitted_package', 'absolute_url')


class CodebaseSerializer(serializers.ModelSerializer):
    all_contributors = CodebaseContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(read_only=True, many=True)
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    last_modified = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = home_serializers.TagSerializer(many=True)
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True)
    submitter = home_serializers.CreatorSerializer(read_only=True)

    @staticmethod
    def get_summary(obj):
        if obj.summary:
            return obj.summary
        else:
            return shorten(obj.description, width=500)

    def create(self, validated_data):
        return home_serializers.create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return home_serializers.update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        exclude = ('featured_images',)
