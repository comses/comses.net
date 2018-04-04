# This module exists to avoid circular imports between home and library files

import logging

from django.contrib.auth.models import User
from rest_framework import serializers

logger = logging.getLogger(__name__)


class RelatedMemberProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    institution_name = serializers.CharField(source='member_profile.institution.name', read_only=True)
    institution_url = serializers.URLField(source='member_profile.institution.url', read_only=True)
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    username = serializers.CharField()

    def get_full_name(self, instance):
        full_name = instance.get_full_name()
        if not full_name:
            full_name = instance.username
        return full_name

    class Meta:
        model = User
        fields = ('full_name', 'institution_name', 'institution_url',
                  'profile_url', 'username')