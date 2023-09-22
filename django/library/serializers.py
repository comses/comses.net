import logging
from collections import defaultdict

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail.images.models import SourceImageIOError

from core.models import MemberProfile
from core.validators import validate_affiliations
from core.serializers import (
    YMD_DATETIME_FORMAT,
    DATE_PUBLISHED_FORMAT,
    FULL_DATETIME_FORMAT,
    create,
    update,
    set_tags,
    TagSerializer,
    MarkdownField,
)

from core.serializers import (
    RelatedMemberProfileSerializer,
    RelatedUserSerializer,
)
from .models import (
    ReleaseContributor,
    Codebase,
    CodebaseRelease,
    CodebaseReleaseDownload,
    Contributor,
    License,
    CodebaseImage,
    PeerReviewerFeedback,
    PeerReviewInvitation,
    PeerReviewEventLog,
)

logger = logging.getLogger(__name__)


class LicenseSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        license = License.objects.filter(name=validated_data["name"]).first()
        if license is not None:
            if validated_data["url"] != license.url:
                license.url = validated_data["url"]
                license.save()
        else:
            license = super().create(validated_data)

        return license

    class Meta:
        model = License
        fields = (
            "name",
            "url",
        )


class ContributorSerializer(serializers.ModelSerializer):
    # Need an ID for Vue-Multiselect
    id = serializers.IntegerField(read_only=True)
    user = RelatedUserSerializer(required=False, allow_null=True)
    affiliations = TagSerializer(many=True)
    profile_url = serializers.SerializerMethodField(read_only=True)

    def get_existing_contributor(self, validated_data):
        user = validated_data.get("user")
        username = user.get("username") if user else None
        email = validated_data.get("email")
        contributor = None
        # attempt to find contributor by username, then email, then name without an email
        if username:
            user = User.objects.filter(username=username).first()
            contributor = Contributor.objects.filter(user__username=username).first()
        elif email:
            contributor = Contributor.objects.filter(email=email).first()
            user = contributor.user if contributor else None
        else:
            contrib_filter = {
                k: validated_data.get(k, "")
                for k in ["given_name", "family_name", "email"]
            }
            contributor = Contributor.objects.filter(**contrib_filter).first()
            user = None

        return user, contributor

    def save(self, **kwargs):
        if self.instance is None:
            validated_data = dict(
                list(self.validated_data.items()) + list(kwargs.items())
            )
            user, self.instance = self.get_existing_contributor(validated_data)
            if user:
                kwargs["user_id"] = user.id
        self.validated_data.pop("user")
        return super().save(**kwargs)

    def get_profile_url(self, instance):
        user = instance.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(
                reverse("core:profile-list"), urlencode({"query": instance.name})
            )

    def update(self, instance, validated_data):
        affiliations = validated_data.pop("affiliations", None)
        validated_data.pop("given_name", None)
        validated_data.pop("family_name", None)
        instance = super().update(instance, validated_data)
        if affiliations:  # dont overwrite affiliations if not provided
            affiliations_serializer = TagSerializer(
                many=True, data=affiliations, context=self.context
            )
            set_tags(instance, affiliations_serializer, "affiliations")
        instance.save()
        return instance

    def create(self, validated_data):
        affiliations_serializer = TagSerializer(
            many=True, data=validated_data.pop("affiliations")
        )
        instance = super().create(validated_data)
        set_tags(instance, affiliations_serializer, "affiliations")
        instance.save()
        return instance

    class Meta:
        model = Contributor
        fields = (
            "id",
            "given_name",
            "middle_name",
            "family_name",
            "name",
            "email",
            "user",
            "type",
            "affiliations",
            "primary_affiliation_name",
            "profile_url",
        )


class ListReleaseContributorSerializer(serializers.ListSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        self.check_unique_users([rc["contributor"] for rc in attrs])
        return attrs

    def check_unique_users(self, contributors):
        user_map = defaultdict(list)
        for contributor in contributors:
            raw_user = contributor["user"]
            if raw_user:
                username = raw_user["username"]
                user_map[username].append(contributor)

        error_messages = []
        for username, related_contributors in user_map.items():
            related_contributor_count = len(related_contributors)
            if related_contributor_count > 1:
                error_messages.append(
                    (
                        f'Validation Error: "{username}" was listed {related_contributor_count} times in the contributors list.'
                        f"Please remove all duplicates and assign multiple roles to them instead."
                    )
                )
        if error_messages:
            raise ValidationError({"non_field_errors": error_messages})

    def create(self, validated_data):
        ReleaseContributor.objects.filter(
            release_id=self.context["release_id"]
        ).delete()
        release_contributors = []
        for i, attr in enumerate(validated_data):
            attr["index"] = i
            release_contributors.append(
                ReleaseContributorSerializer.create_unsaved(self.context, attr)
            )

        ReleaseContributor.objects.bulk_create(release_contributors)
        return release_contributors


class FeaturedImageMixin(serializers.Serializer):
    featured_image = serializers.SerializerMethodField()

    def get_featured_image(self, instance):
        featured_image = instance.get_featured_image()
        request = self.context.get("request")
        if featured_image:
            if request and request.accepted_media_type != "text/html":
                try:
                    return featured_image.get_rendition("width-780").url
                except SourceImageIOError as e:
                    logger.error(e)
                    return None
            else:
                return featured_image
        else:
            return None


class ReleaseContributorSerializer(serializers.ModelSerializer):
    contributor = ContributorSerializer()
    profile_url = serializers.SerializerMethodField(read_only=True)
    index = serializers.IntegerField(required=False)

    def get_profile_url(self, instance):
        user = instance.contributor.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(
                reverse("core:profile-list"),
                urlencode({"query": instance.contributor.name}),
            )

    @staticmethod
    def create_unsaved(context, validated_data):
        raw_contributor = validated_data.pop("contributor")
        contributor_serializer = ContributorSerializer(data=raw_contributor)
        contributor_serializer.is_valid(raise_exception=True)
        contributor = contributor_serializer.save()

        validated_data["release_id"] = context["release_id"]
        validated_data["contributor_id"] = contributor.id
        instance = ReleaseContributor(**validated_data)
        return instance

    def update_codebase_contributor_cache(self, contributor):
        Codebase.objects.cache_contributors(
            Codebase.objects.with_contributors().filter(
                releases__codebase_contributors__contributor=contributor
            )
        )

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
        fields = (
            "contributor",
            "profile_url",
            "include_in_citation",
            "roles",
            "index",
        )


class RelatedCodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(
        source="get_absolute_url",
        read_only=True,
        help_text=_("URL to the detail page of the codebase"),
    )
    release_contributors = ReleaseContributorSerializer(
        read_only=True,
        many=True,
        source="index_ordered_release_contributors",
    )
    submitter = RelatedUserSerializer(read_only=True, label="Submitter")
    first_published_at = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    last_published_on = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )

    class Meta:
        model = CodebaseRelease
        fields = (
            "absolute_url",
            "release_contributors",
            "submitter",
            "first_published_at",
            "last_published_on",
            "version_number",
            "live",
            "status",
        )


class CodebaseSerializer(serializers.ModelSerializer, FeaturedImageMixin):
    absolute_url = serializers.URLField(source="get_absolute_url", read_only=True)
    all_contributors = ContributorSerializer(many=True, read_only=True)
    date_created = serializers.DateTimeField(
        read_only=True, default=serializers.CreateOnlyDefault(timezone.now)
    )
    download_count = serializers.IntegerField(read_only=True)
    first_published_at = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    last_published_on = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    latest_version_number = serializers.ReadOnlyField(
        source="latest_version.version_number"
    )
    releases = serializers.SerializerMethodField()
    submitter = RelatedUserSerializer(
        read_only=True, default=serializers.CurrentUserDefault()
    )
    summarized_description = serializers.CharField(read_only=True)
    identifier = serializers.ReadOnlyField()
    tags = TagSerializer(many=True)

    description = MarkdownField()

    def get_releases(self, obj):
        request = self.context.get("request")
        user = request.user if request else User.get_anonymous()
        queryset = (
            CodebaseRelease.objects.filter(codebase_id=obj.pk)
            .accessible(user)
            .order_by("-version_number")
        )
        # queryset = obj.releases.order_by('-version_number')
        return RelatedCodebaseReleaseSerializer(
            queryset, read_only=True, many=True, context=self.context
        ).data

    def create(self, validated_data):
        serialized_tags = TagSerializer(many=True, data=validated_data.pop("tags"))
        codebase = Codebase(**validated_data)
        codebase.submitter = self.context["request"].user
        codebase.identifier = codebase.uuid
        set_tags(codebase, serialized_tags)
        codebase.save()
        return codebase

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = (
            "absolute_url",
            "all_contributors",
            "date_created",
            "download_count",
            "featured_image",
            "repository_url",
            "first_published_at",
            "last_published_on",
            "latest_version_number",
            "releases",
            "submitter",
            "summarized_description",
            "tags",
            "description",
            "title",
            "doi",
            "identifier",
            "id",
            "references_text",
            "associated_publication_text",
            "replication_text",
            "peer_reviewed",
        )


class RelatedCodebaseSerializer(serializers.ModelSerializer, FeaturedImageMixin):
    """
    Sparse codebase serializer
    """

    all_contributors = ContributorSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True)
    version_number = serializers.ReadOnlyField(source="latest_version.version_number")
    first_published_at = serializers.DateTimeField(
        read_only=True, format=DATE_PUBLISHED_FORMAT
    )
    last_published_on = serializers.DateTimeField(
        read_only=True, format=DATE_PUBLISHED_FORMAT
    )
    summarized_description = serializers.CharField(read_only=True)
    live = serializers.ReadOnlyField()
    description = MarkdownField()

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Codebase
        fields = (
            "all_contributors",
            "tags",
            "title",
            "first_published_at",
            "last_published_on",
            "identifier",
            "version_number",
            "featured_image",
            "summarized_description",
            "description",
            "live",
            "peer_reviewed",
            "repository_url",
        )


class CodebaseImageSerializer(serializers.ModelSerializer):
    identifier = serializers.IntegerField(source="id")
    name = serializers.CharField(source="title")

    def get_url(self, instance):
        return instance.get_rendition("max-200x200").url

    class Meta:
        model = CodebaseImage
        fields = ("identifier", "name", "file")
        extra_kwargs = {"file": {"write_only": True}}


class DownloadRequestSerializer(serializers.ModelSerializer):
    # customize save functionality to validate and record a new CodebaseReleaseDownload
    save_to_profile = serializers.BooleanField()

    def create(self, validated_data):
        logger.debug("creating download request serializer from: %s", validated_data)
        save_to_profile = validated_data.pop("save_to_profile")
        industry = validated_data.get("industry")
        affiliation = validated_data.get("affiliation")
        instance = CodebaseReleaseDownload(**validated_data)
        instance.user = validated_data.get("user")
        # update user's profile to reflect information provided
        if instance.user and save_to_profile:
            self.update_profile(instance, industry, affiliation)
        instance.save()
        return instance

    def update_profile(self, instance, industry, affiliation):
        member_profile = instance.user.member_profile
        member_profile.industry = industry
        if affiliation:
            # check if affiliation with this name already exists in member_profile
            if not any(
                mem_aff["name"] == affiliation["name"]
                for mem_aff in member_profile.affiliations
            ):
                member_profile.affiliations.append(affiliation)
        # run validation on updated member_profile
        try:
            validate_affiliations(member_profile.affiliations)
        except Exception as e:
            raise ValidationError(e.messages)
        else:
            member_profile.save()

    class Meta:
        model = CodebaseReleaseDownload
        fields = (
            "save_to_profile",
            "referrer",
            "reason",
            "ip_address",
            "user",
            "industry",
            "affiliation",
            "release",
        )


class CodebaseReleaseSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(
        source="get_absolute_url",
        read_only=True,
        help_text=_("URL to the detail page of the codebase"),
    )
    citation_text = serializers.ReadOnlyField()
    codebase = CodebaseSerializer(read_only=True)
    release_contributors = ReleaseContributorSerializer(
        read_only=True, source="index_ordered_release_contributors", many=True
    )
    date_created = serializers.DateTimeField(format=YMD_DATETIME_FORMAT, read_only=True)
    first_published_at = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    last_published_on = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    license = LicenseSerializer()
    live = serializers.ReadOnlyField()
    can_edit_originals = serializers.ReadOnlyField()
    os_display = serializers.ReadOnlyField(source="get_os_display")
    platforms = TagSerializer(many=True, source="platform_tags")
    programming_languages = TagSerializer(many=True)
    submitter = RelatedUserSerializer(read_only=True, label="Submitter")
    version_number = serializers.ReadOnlyField()
    release_notes = MarkdownField(max_length=2048)
    urls = serializers.SerializerMethodField()
    review_status = serializers.SerializerMethodField()

    def get_urls(self, instance):
        request_peer_review_url = instance.get_request_peer_review_url()
        review = instance.get_review()
        review_url = review.get_absolute_url() if review else None
        notify_reviewers_of_changes_url = (
            instance.get_notify_reviewers_of_changes_url() if review else None
        )
        return {
            "request_peer_review": request_peer_review_url,
            "review": review_url,
            "notify_reviewers_of_changes": notify_reviewers_of_changes_url,
        }

    def get_review_status(self, instance):
        return instance.review.status if instance.get_review() else None

    class Meta:
        model = CodebaseRelease
        fields = (
            "absolute_url",
            "can_edit_originals",
            "citation_text",
            "release_contributors",
            "date_created",
            "dependencies",
            "release_notes",
            "documentation",
            "doi",
            "download_count",
            "embargo_end_date",
            "first_published_at",
            "last_modified",
            "last_published_on",
            "license",
            "live",
            "os",
            "os_display",
            "peer_reviewed",
            "platforms",
            "programming_languages",
            "submitted_package",
            "submitter",
            "codebase",
            "review_status",
            "output_data_url",
            "version_number",
            "id",
            "share_url",
            "urls",
        )


class CodebaseReleaseEditSerializer(CodebaseReleaseSerializer):
    possible_licenses = serializers.SerializerMethodField()

    def get_possible_licenses(self, instance):
        serialized = LicenseSerializer(
            License.objects.order_by("name").all(), many=True
        )
        return serialized.data

    def update(self, instance, validated_data):
        programming_languages = TagSerializer(
            many=True, data=validated_data.pop("programming_languages")
        )
        platform_tags = TagSerializer(
            many=True, data=validated_data.pop("platform_tags")
        )

        raw_license = validated_data.pop("license")
        existing_license = License.objects.get(name=raw_license["name"])

        set_tags(instance, programming_languages, "programming_languages")
        set_tags(instance, platform_tags, "platform_tags")

        instance = super().update(instance, validated_data)

        instance.license = existing_license
        instance.save()

        return instance

    def save_release_contributors(
        self,
        instance: CodebaseRelease,
        release_contributors_serializer: ReleaseContributorSerializer,
    ):
        release_contributors_serializer.is_valid(raise_exception=True)
        release_contributors = release_contributors_serializer.save()

        # Old contributors are not deleted from the database
        instance.contributors.clear()
        instance.codebase_contributors = release_contributors

    class Meta:
        model = CodebaseRelease
        fields = CodebaseReleaseSerializer.Meta.fields + ("possible_licenses",)


class PeerReviewFeedbackEditorSerializer(serializers.ModelSerializer):
    editor_url = serializers.CharField(source="get_editor_url")
    reviewer_name = serializers.SerializerMethodField()
    review_status = serializers.SerializerMethodField()

    def get_review_status(self, instance):
        return instance.invitation.review.get_status_display()

    def get_reviewer_name(self, instance):
        return instance.invitation.candidate_reviewer.name

    class Meta:
        model = PeerReviewerFeedback
        fields = "__all__"
        read_only_fields = (
            "date_created",
            "invitation",
            "recommendation",
            "reviewer",
            "private_reviewer_notes",
            "notes_to_author",
            "editor_url",
            "has_narrative_documentation",
            "narrative_documentation_comments",
            "has_clean_code",
            "clean_code_comments",
            "is_runnable",
            "reviewer_name",
            "runnable_comments",
        )


class PeerReviewInvitationSerializer(serializers.ModelSerializer):
    """Serialize review invitations. Build for list, detail and create routes
    (updating a peer review invitation may not make sense since an email has
    already been sent)"""

    url = serializers.ReadOnlyField(source="get_absolute_url")
    candidate_reviewer = RelatedMemberProfileSerializer(read_only=True)
    expiration_date = serializers.SerializerMethodField()

    def get_expiration_date(self, obj):
        return format(obj.expiration_date, FULL_DATETIME_FORMAT)

    class Meta:
        model = PeerReviewInvitation
        fields = "__all__"
        read_only_fields = ("date_created",)


class RelatedPeerReviewInvitationSerializer(serializers.ModelSerializer):
    url = serializers.ReadOnlyField(source="get_absolute_url")
    latest_feedback_url = serializers.SerializerMethodField()
    codebase_release_title = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_latest_feedback_url(self, instance):
        return instance.latest_feedback.get_absolute_url()

    def get_codebase_release_title(self, instance):
        release = instance.review.codebase_release
        version_number = release.version_number
        title = release.codebase.title
        return "{} {}".format(title, version_number)

    def get_status(self, instance):
        return instance.review.get_status_display()

    class Meta:
        model = PeerReviewInvitation
        fields = (
            "date_created",
            "optional_message",
            "accepted",
            "url",
            "latest_feedback_url",
            "codebase_release_title",
            "status",
        )
        read_only_fields = ("date_created",)


class AuthorSerializer(serializers.ModelSerializer):
    absolute_url = serializers.URLField(source="get_absolute_url")

    class Meta:
        model = MemberProfile
        fields = ("name", "absolute_url")


class PeerReviewEventLogSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    date_created = serializers.DateTimeField(format="%I:%M%p %b %d, %Y")

    class Meta:
        model = PeerReviewEventLog
        fields = (
            "date_created",
            "review",
            "action",
            "author",
            "message",
        )
