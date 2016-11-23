from rest_framework import serializers
from .models import Author, Event, Job, Model, ModelVersion, Keyword
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'


class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


class JobSerializer(serializers.ModelSerializer):
    creator = CreatorSerializer(read_only=True, help_text=_('User that created the job description'))
    url = serializers.SerializerMethodField(help_text=_('URL to the detail page of the job'))

    def get_url(self, obj):
        return reverse_lazy('job-detail', kwargs={'pk': obj.id})

    class Meta:
        model = Job
        fields = ('id', 'title', 'creator', 'date_created', 'content', 'url')


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = ('id', 'content')


class ModelSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    creator = CreatorSerializer(read_only=True)
    modelversion_set = ModelVersionSerializer(many=True)
    keywords = serializers.StringRelatedField(many=True)

    class Meta:
        model = Model
        fields = '__all__'
