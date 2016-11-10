from rest_framework import serializers
from .models import Event, Job, Model, ModelVersion, Keyword
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'


class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


class JobSerializer(serializers.ModelSerializer):
    creator = CreatorSerializer(read_only=True)
    url = serializers.SerializerMethodField()

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
    creator = CreatorSerializer(read_only=True)
    modelversion_set = ModelVersionSerializer(many=True)
    keywords = serializers.StringRelatedField(many=True)

    class Meta:
        model = Model
        fields = '__all__'