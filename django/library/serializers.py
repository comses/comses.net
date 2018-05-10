import logging

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from wagtail.images.models import SourceImageIOError

from core.models import MemberProfile
from core.serializers import (YMD_DATETIME_FORMAT, PUBLISH_DATE_FORMAT, LinkedUserSerializer, create, update, save_tags,
                              TagSerializer, MarkdownField)
from home.common_serializers import RelatedMemberProfileSerializer
from .models import (ReleaseContributor, Codebase, CodebaseRelease, Contributor, License, CodebaseImage, PeerReview,
                     PeerReviewerFeedback, PeerReviewInvitation)

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        license = License.objects.filter(name=validated_data['name']).first()
        if license is not None:
            if validated_data['url'] != license.url:
                license.url = validated_data['url']
                license.save()
        else:
            license = super().create(validated_data)

        return license

    class Meta:
        model = License
        fields = ('name', 'url',)


class ContributorSerializer(serializers.ModelSerializer):
    # Need an ID for Vue-Multiselect
    id = serializers.IntegerField(read_only=True)
    user = RelatedMemberProfileSerializer(required=False, allow_null=True)
    affiliations = TagSerializer(many=True)
    profile_url = serializers.SerializerMethodField()

    def get_profile_url(self, instance):
        user = instance.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(reverse('home:profile-list'), urlencode({'query': instance.name}))

    def _create_or_update(self, validated_data):
        affiliations_serializer = TagSerializer(many=True, data=validated_data.pop('affiliations'))
        raw_user = validated_data.pop('user')
        if raw_user:
            user = User.objects.get(username=raw_user['username'])
        else:
            user = None
        validated_data['user_id'] = user.id if user else None
        return affiliations_serializer, user

    def update(self, instance, validated_data):
        affiliations_serializer = TagSerializer(many=True, data=validated_data.pop('affiliations'))
        instance = super().update(instance, validated_data)
        save_tags(instance, affiliations_serializer, 'affiliations')
        instance.save()
        return instance

    def create(self, validated_data):
        affiliations_list_serializer, user = self._create_or_update(validated_data)
        instance = super().create(validated_data)
        save_tags(instance, affiliations_list_serializer, 'affiliations')
        instance.save()
        return instance

    class Meta:
        model = Contributor
        fields = ('id', 'given_name', 'middle_name', 'family_name', 'name', 'email', 'user', 'type', 'affiliations',
                  'profile_url')


class ListReleaseContributorSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        ReleaseContributor.objects.filter(release_id=self.context['release_id']).delete()
        release_contributors = []
        for i, attr in enumerate(validated_data):
            attr['index'] = i
            release_contributors.append(ReleaseContributorSerializer.create_unsaved(self.context, attr))

        ReleaseContributor.objects.bulk_create(release_contributors)
        return release_contributors


class FeaturedImageMixin(serializers.Serializer):
    featured_image = serializers.SerializerMethodField()

    def get_featured_image(self, instance):
        featured_image = instance.get_featured_image()
        request = self.context.get('request')
        if featured_image:
            if request and request.accepted_media_type != 'text/html':
                try:
                    return featured_image.get_rendition('width-780').url
                except SourceImageIOError as e:
                    logger.error(e)
                    return None
            else:
                return featured_image
        else:
            return None


class ReleaseContributorSerializer(serializers.ModelSerializer):
    contributor = ContributorSerializer()
    profile_url = serializers.SerializerMethodField()
    index = serializers.IntegerField(required=False)

    def get_profile_url(self, instance):
        user = instance.contributor.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(reverse('home:profile-list'), urlencode({'query': instance.contributor.name}))

    @staticmethod
    def create_unsaved(context, validated_data):
        contributor_serializer = ContributorSerializer()
        contributor_serializer._errors = {}
        raw_contributor = validated_data.pop('contributor')
        kwargs = {'given_name': raw_contributor['given_name'], 'family_name': raw_contributor['family_name']}
        if raw_contributor.get('user'):
            kwargs = {'user__username': raw_contributor['user']['username']}
        contributor = Contributor.objects.filter(**kwargs).first()
        if contributor:
            raw_contributor.pop('user')
            contributor = contributor_serializer.update(instance=contributor, validated_data=raw_contributor)
        else:
            contributor = contributor_serializer.create(raw_contributor)

        validated_data['release_id'] = context['release_id']
        validated_data['contributor_id'] = contributor.id
        instance = ReleaseContributor(**validated_data)
        return instance

    def update_codebase_contributor_cache(self, contributor):
        Codebase.objects.cache_contributors(
            Codebase.objects.with_contributors().filter(
                releases__codebase_contributors__contributor=contributor))

    def create(self, validated_data):
        release_contributor = self.create_unsaved(self.context, validated_data)
        release_contributor.save()
        self.update_codebase_contributor_cache(release_contributor.contributor)
        return release_contributor

    def update(self, instance, validated_data):
        release_contributor = super().update(instance, validated_data)
        self.update_codebase_contributor_cache(release_contributor.contributor)
        return release_contributor

    class Meta:
        list_serializer_class = ListReleaseContributorSerializer
        model = ReleaseContributor
        fields = ('contributor', 'profile_url', 'include_in_citation', 'roles', 'index',)


class RelatedCodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    release_contributors = ReleaseContributorSerializer(read_only=True, many=True,
                                                        source='index_ordered_release_contributors', )
    submitter = LinkedUserSerializer(read_only=True, label='Submitter')
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)

    class Meta:
        model = CodebaseRelease
        fields = ('absolute_url', 'release_contributors', 'submitter', 'first_published_at', 'last_published_on',
                  'version_number', 'live', 'draft',)


class CodebaseSerializer(serializers.ModelSerializer, FeaturedImageMixin):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True)
    all_contributors = ContributorSerializer(many=True, read_only=True)
    date_created = serializers.DateTimeField(read_only=True,
                                             default=serializers.CreateOnlyDefault(timezone.now))
    download_count = serializers.IntegerField(read_only=True)
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    latest_version_number = serializers.ReadOnlyField(source='latest_version.version_number')
    releases = serializers.SerializerMethodField()
    submitter = LinkedUserSerializer(read_only=True,
                                     default=serializers.CurrentUserDefault())
    summarized_description = serializers.CharField(read_only=True)
    identifier = serializers.ReadOnlyField()
    tags = TagSerializer(many=True)

    # FIXME: output should be raw markdown, not rendered
    description = MarkdownField()

    def get_releases(self, obj):
        request = self.context.get('request')
        user = request.user if request else User.get_anonymous()
        queryset = CodebaseRelease.objects.filter(codebase_id=obj.pk).accessible(user).order_by('-version_number')
        # queryset = obj.releases.order_by('-version_number')
        return RelatedCodebaseReleaseSerializer(
            queryset, read_only=True, many=True, context=self.context
        ).data

    def create(self, validated_data):
        serialized_tags = TagSerializer(many=True, data=validated_data.pop('tags'))
        codebase = Codebase(**validated_data)
        codebase.submitter = self.context['request'].user
        codebase.identifier = codebase.uuid
        codebase.save()
        save_tags(codebase, serialized_tags)
        return codebase

    def update(self, instance, validated_data):
        validated_data['draft'] = False
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = ('absolute_url', 'all_contributors', 'date_created', 'download_count', 'featured_image',
                  'repository_url', 'first_published_at', 'last_published_on', 'latest_version_number',
                  'releases', 'submitter', 'summarized_description', 'tags', 'description', 'title',
                  'doi', 'identifier', 'id', 'references_text', 'associated_publication_text', 'replication_text',
                  'peer_reviewed',)


class RelatedCodebaseSerializer(serializers.ModelSerializer, FeaturedImageMixin):
    """
    Sparse codebase serializer
    """
    all_contributors = ContributorSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    version_number = serializers.ReadOnlyField(source='latest_version.version_number')
    first_published_at = serializers.DateTimeField(read_only=True, format=PUBLISH_DATE_FORMAT)
    last_published_on = serializers.DateTimeField(read_only=True, format=PUBLISH_DATE_FORMAT)
    summarized_description = serializers.CharField(read_only=True)
    live = serializers.SerializerMethodField()

    def get_live(self, instance):
        return instance.live

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = ('all_contributors', 'tags', 'title', 'first_published_at', 'last_published_on', 'identifier',
                  'version_number', 'featured_image', 'summarized_description', 'description', 'live', 'peer_reviewed',
                  'repository_url',)


class CodebaseImageSerializer(serializers.ModelSerializer):
    identifier = serializers.IntegerField(source='id')
    name = serializers.CharField(source='title')

    def get_url(self, instance):
        return instance.get_rendition('max-200x200').url

    class Meta:
        model = CodebaseImage
        fields = ('identifier', 'name', 'file')
        extra_kwargs = {
            'file': {'write_only': True}
        }


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source='get_absolute_url', read_only=True,
                                        help_text=_('URL to the detail page of the codebase'))
    citation_text = serializers.ReadOnlyField()
    codebase = CodebaseSerializer(read_only=True)
    release_contributors = ReleaseContributorSerializer(read_only=True, source='index_ordered_release_contributors',
                                                        many=True)
    date_created = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    first_published_at = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    last_published_on = serializers.DateTimeField(format=PUBLISH_DATE_FORMAT, read_only=True)
    license = LicenseSerializer()
    live = serializers.ReadOnlyField()
    os_display = serializers.ReadOnlyField(source='get_os_display')
    platforms = TagSerializer(many=True, source='platform_tags')
    programming_languages = TagSerializer(many=True)
    submitter = LinkedUserSerializer(read_only=True, label='Submitter')
    version_number = serializers.ReadOnlyField()
    release_notes = MarkdownField()
    has_review = serializers.SerializerMethodField()

    def get_has_review(self, instance):
        if hasattr(instance, 'review'):
            return True
        return False

    class Meta:
        model = CodebaseRelease
        fields = ('absolute_url', 'citation_text', 'release_contributors', 'date_created', 'dependencies',
                  'release_notes', 'documentation', 'doi', 'download_count', 'embargo_end_date', 'first_published_at',
                  'last_modified', 'last_published_on', 'license', 'live', 'os', 'os_display', 'peer_reviewed',
                  'platforms', 'programming_languages', 'has_review', 'submitted_package', 'submitter', 'codebase',
                  'version_number', 'id', 'share_url',)


class CodebaseReleaseEditSerializer(CodebaseReleaseSerializer):
    possible_licenses = serializers.SerializerMethodField()

    def get_possible_licenses(self, instance):
        serialized = LicenseSerializer(License.objects.all(), many=True)
        return serialized.data

    def update(self, instance, validated_data):
        programming_languages = TagSerializer(many=True, data=validated_data.pop('programming_languages'))
        platform_tags = TagSerializer(many=True, data=validated_data.pop('platform_tags'))

        raw_license = validated_data.pop('license')
        existing_license = License.objects.get(name=raw_license['name'])

        save_tags(instance, programming_languages, 'programming_languages')
        save_tags(instance, platform_tags, 'platform_tags')

        instance = super().update(instance, validated_data)

        instance.license = existing_license
        instance.draft = False
        instance.save()

        return instance

    def save_release_contributors(self, instance: CodebaseRelease,
                                  release_contributors_serializer: ReleaseContributorSerializer):
        release_contributors_serializer.is_valid(raise_exception=True)
        release_contributors = release_contributors_serializer.save()

        # Old contributors are not deleted from the database
        instance.contributors.clear()
        instance.codebase_contributors = release_contributors

    class Meta:
        model = CodebaseRelease
        fields = CodebaseReleaseSerializer.Meta.fields + ('possible_licenses',)


class PeerReviewFeedbackEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerReviewerFeedback
        fields = '__all__'
        read_only_fields = ('date_created', 'invitation', 'recommendation', 'reviewer',
                            'private_reviewer_notes', 'notes_to_author',
                            'has_narrative_documentation', 'narrative_documentation_comments',
                            'has_clean_code', 'clean_code_comments',
                            'is_runnable', 'runnable_comments')


class PeerReviewReviewerSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)

    # annotated fields
    n_pending_reviews = serializers.IntegerField()
    n_total_reviews = serializers.IntegerField()

    class Meta:
        model = MemberProfile
        fields = ('id', 'avatar_url', 'degrees', 'name', 'n_pending_reviews', 'n_total_reviews', 'tags',)


class PeerReviewInvitationSerializer(serializers.ModelSerializer):
    """Serialize review invitations. Build for list, detail and create routes
    (updating a peer review invitation may not make sense since an email has
    already been sent)"""
    url = serializers.ReadOnlyField(source='get_absolute_url')

    candidate_reviewer = PeerReviewReviewerSerializer(read_only=True)

    class Meta:
        model = PeerReviewInvitation
        fields = '__all__'
        read_only_fields = ('date_created',)


class RelatedPeerReviewInvitationSerializer(serializers.ModelSerializer):
    url = serializers.ReadOnlyField(source='get_absolute_url')
    codebase_release_title = serializers.SerializerMethodField()

    def get_codebase_release_title(self, instance):
        release = instance.review.codebase_release
        version_number = release.version_number
        title = release.codebase.title
        return '{} {}'.format(title, version_number)

    class Meta:
        model = PeerReviewInvitation
        fields = ('date_created', 'optional_message', 'accepted', 'url', 'codebase_release_title')
        read_only_fields = ('date_created',)