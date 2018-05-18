# This module exists to avoid circular imports between home and library files

import logging

from django.contrib.auth.models import User
from rest_framework import serializers

logger = logging.getLogger(__name__)


class RelatedMemberProfileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    institution_name = serializers.CharField(source='member_profile.institution.name', read_only=True)
    institution_url = serializers.URLField(source='member_profile.institution.url', read_only=True)
    profile_url = serializers.URLField(source='member_profile.get_absolute_url', read_only=True)
    username = serializers.CharField()

    def get_name(self, instance):
        name = instance.get_full_name()
        if not name:
            name = instance.username
        return name

    class Meta:
        model = User
        fields = ('name', 'institution_name', 'institution_url',
                  'profile_url', 'username')