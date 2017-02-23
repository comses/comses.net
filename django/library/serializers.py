from rest_framework import serializers

from .models import CodebaseContributor, Codebase, CodebaseRelease


class CodebaseContributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodebaseContributor
        fields = '__all__'


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodebaseRelease
        fields = '__all__'


class CodebaseSerializer(serializers.ModelSerializer):
    contributors = CodebaseContributorSerializer(many=True, read_only=True)
    releases = CodebaseReleaseSerializer(many=True)
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Codebase
        fields = '__all__'
