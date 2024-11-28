from rest_framework import serializers

from core.models import Event, Job, MemberProfile, SpamModeration
from library.models import Codebase


class SpamModerationSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source="content_type.model")

    class Meta:
        model = SpamModeration
        fields = [
            "id",
            # "status",
            "content_type",
            "object_id",
            # "date_created",
            # "last_modified",
            # "notes",
            # "detection_method",
            # "detection_details",
        ]


class MinimalJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "summary",
            "description",
            "external_url",
        ]


class MinimalEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "summary",
            "description",
            "external_url",
        ]


class MinimalCodebaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Codebase
        fields = [
            "id",
            "title",
            "description",
        ]


class MinimalMemberProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = [
            "id",
            "username",
            "name",
            "email",
            "bio",
            "research_interests",
            "affiliations_string",
            "degrees",
            "personal_url",
            "professional_url",
        ]


class SpamUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_spam = serializers.BooleanField()
    spam_indicators = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    reasoning = serializers.CharField(required=False)
    confidence = serializers.FloatField(required=False)
