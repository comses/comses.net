from rest_framework import serializers
from .models import Event, Job
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _


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
