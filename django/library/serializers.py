from rest_framework import serializers

from .models import CodebaseContributor, Codebase, CodebaseRelease
from core.serializer_helpers import EditableSerializerMixin, save_tags
from home import serializers as home_serializers
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _


class CodebaseContributorSerializer(serializers.ModelSerializer, EditableSerializerMixin):

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
    releases = CodebaseReleaseSerializer(read_only=True, many=True)
    date_created = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    tags = home_serializers.TagSerializer(many=True)
    url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the codebase'))
    submitter = home_serializers.CreatorSerializer(read_only=True)

    def get_url(self, obj):
        return reverse_lazy('library:codebase-detail', kwargs={'pk': obj.id})

    def create(self, validated_data):
        return home_serializers.create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return home_serializers.update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = '__all__'
