from rest_framework import serializers

from .models import Author, Code, CodeRelease

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class CodeReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeRelease
        fields = ('id', 'content')


class CodeSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    code_releases = CodeReleaseSerializer(many=True)
    keywords = serializers.StringRelatedField(many=True)

    class Meta:
        model = Code
        fields = '__all__'
