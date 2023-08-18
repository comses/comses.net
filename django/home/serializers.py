import logging

from rest_framework import serializers

from .models import FeaturedContentItem, UserMessage

logger = logging.getLogger(__name__)


class FeaturedContentItemSerializer(serializers.ModelSerializer):
    image = serializers.SlugRelatedField(read_only=True, slug_field="file")

    class Meta:
        model = FeaturedContentItem
        fields = (
            "image",
            "caption",
            "title",
        )


class UserMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMessage
        fields = ("message", "user")
