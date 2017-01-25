from rest_framework import serializers

from .models import Contributor, Codebase, CodebaseRelease


class ContributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodebaseRelease
        fields = '__all__'


class CodebaseSerializer(serializers.ModelSerializer):
    contributors = ContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(many=True)
    keywords = serializers.StringRelatedField(many=True)

    class Meta:
        model = Codebase
        fields = '__all__'
