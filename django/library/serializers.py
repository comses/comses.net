from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from textwrap import shorten
from core.serializer_helpers import EditableSerializerMixin
from home import serializers as home_serializers
from .models import CodebaseContributor, Codebase, CodebaseRelease


class CodebaseContributorSerializer(serializers.ModelSerializer, EditableSerializerMixin):

    user = serializers.ReadOnlyField(source='contributor.user')
    contributor = serializers.ReadOnlyField(source='contributor.get_full_name')
    affiliations = serializers.ReadOnlyField(source='contributor.formatted_affiliations')

    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer, EditableSerializerMixin):
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the codebase'))

    def get_url(self, obj):
        return reverse_lazy('library:codebaserelease-detail', kwargs={'uuid': obj.codebase_id, 'pk': obj.id})

    class Meta:
        model = CodebaseRelease
        fields = '__all__'


class CodebaseSerializer(serializers.ModelSerializer):
    contributors = CodebaseContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(many=True, read_only=True)
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = home_serializers.TagSerializer(many=True)
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    submitter = home_serializers.CreatorSerializer(read_only=True)
    summary = serializers.SerializerMethodField()
    last_modified = serializers.DateTimeField(format='%c', read_only=True)

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
        fields = '__all__'
