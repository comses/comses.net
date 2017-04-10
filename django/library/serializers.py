from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from textwrap import shorten
from .models import Contributor, CodebaseContributor, Codebase, CodebaseRelease
from home import serializers as home_serializers
from .models import CodebaseContributor, Codebase, CodebaseRelease


class ContributorSerializer(serializers.ModelSerializer):
    user = home_serializers.CreatorSerializer()

    class Meta:
        model = Contributor
        fields = ('name', 'email', 'user',)


class CodebaseContributorSerializer(serializers.ModelSerializer):
    contributor = ContributorSerializer()

    user = serializers.ReadOnlyField(source='contributor.user')
    contributor = serializers.ReadOnlyField(source='contributor.get_full_name')
    affiliations = serializers.ReadOnlyField(source='contributor.formatted_affiliations')

    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    relative_url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the codebase'))
    codebase_contributors = CodebaseContributorSerializer(many=True)
    submitter = home_serializers.UserSerializer(label='Submitter')
    platforms = home_serializers.TagSerializer(many=True)
    programming_languages = home_serializers.TagSerializer(many=True)

    def get_relative_url(self, obj) -> str:
        return reverse_lazy('library:codebaserelease-detail',
                            kwargs={'pk': obj.codebase.identifier, 'version_number': obj.version_number})

    class Meta:
        model = CodebaseRelease
        fields = ('date_created', 'last_modified', 'peer_reviewed', 'doi', 'description', 'license', 'documentation',
                  'embargo_end_date', 'version_number', 'os', 'platforms', 'programming_languages', 'submitter',
                  'codebase_contributors', 'submitted_package', 'relative_url')


class CodebaseSerializer(serializers.ModelSerializer):
    all_contributors = CodebaseContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(read_only=True, many=True)
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    last_modified = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = home_serializers.TagSerializer(many=True)
    absolute_url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the codebase'))
    submitter = home_serializers.CreatorSerializer(read_only=True)

    @staticmethod
    def get_summary(obj):
        if obj.summary:
            return obj.summary
        else:
            return shorten(obj.description, width=500)

    def get_absolute_url(self, obj) -> str:
        return reverse_lazy('library:codebase-detail', kwargs={'pk': obj.id})

    def create(self, validated_data):
        return home_serializers.create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return home_serializers.update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = '__all__'
