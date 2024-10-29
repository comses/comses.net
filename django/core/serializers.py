import logging

from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from markupfield.fields import Markup
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DrfValidationError
from taggit.models import Tag

from .validators import validate_affiliations
from .models import Event, Job, MemberProfile
from .mixins import SpamCatcherSerializerMixin

logger = logging.getLogger(__name__)

YMD_DATETIME_FORMAT = "%Y-%m-%d"
DATE_PUBLISHED_FORMAT = "%b %d, %Y"
FULL_DATE_FORMAT = "%A, %B %d, %Y"
FULL_DATETIME_FORMAT = "%a, %b %d, %Y at %I:%M %p"

ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TagListSerializer(serializers.ListSerializer):
    """
    FIXME: needs to implement update & create from base class.
    """

    def save(self, **kwargs):
        data_mapping = {item["name"]: item for item in self.validated_data}

        # Perform creations and updates.
        tags = []
        for tag_name, data in data_mapping.items():
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)

        return tags


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=Tag._meta.get_field("name").max_length
    )  # disable uniqueness check so TagListSerializer will validate properly

    class Meta:
        model = Tag
        fields = ("name",)
        list_serializer_class = TagListSerializer


def create(model_cls, validated_data, context):
    # Create related many to many
    tags = TagSerializer(many=True, data=validated_data.pop("tags"))
    # Add read only properties without defaults
    user = context["request"].user
    validated_data["submitter_id"] = user.id
    # Relate with other many to many relations
    obj = model_cls.objects.create(**validated_data)
    set_tags(obj, tags)
    obj.save()
    return obj


def update(serializer_update, instance, validated_data):
    tags = TagSerializer(many=True, data=validated_data.pop("tags"))
    instance = serializer_update(instance, validated_data)
    set_tags(instance, tags)
    instance.save()
    return instance


class EditableSerializerMixin(serializers.Serializer):
    editable = serializers.SerializerMethodField(
        help_text=_("Whether or not entity is editable by the current user")
    )

    def get_editable(self, obj):
        # logger.debug(self.context)
        request = self.context.get("request")
        if request is None:
            return False

        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        return request.user.has_perm("{}.change_{}".format(app_label, model_name), obj)


def set_tags(instance, related, attr="tags"):
    """Associate taggit tags with an instance.

    Instance must be saved afterward for associations to be saved in the db"""
    if not related.is_valid():
        raise serializers.ValidationError(related.errors)
    db_tags = related.save()
    # TaggableManager.set now accepts a list of tags as a single argument instead of a variable number of arguments as
    # of django-taggit 2.x and wagtail 2.16+

    getattr(instance, attr).set(db_tags)


class MarkdownField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_blank", True)
        super().__init__(*args, **kwargs)

    def to_representation(self, obj):
        if isinstance(obj, Markup):
            return obj.raw
        return obj

    def to_internal_value(self, data):
        return data


class MemberProfileSerializer(serializers.ModelSerializer):
    # User fields
    date_joined = serializers.DateTimeField(
        source="user.date_joined", read_only=True, format="%B %d %Y"
    )
    family_name = serializers.CharField(source="user.last_name")
    given_name = serializers.CharField(source="user.first_name")
    username = serializers.CharField(source="user.username", read_only=True)
    user_pk = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.SerializerMethodField()

    # Followers
    follower_count = serializers.ReadOnlyField(source="user.following.count")
    following_count = serializers.ReadOnlyField(source="user.followers.count")

    # MemberProfile
    affiliations = serializers.JSONField()
    avatar = (
        serializers.SerializerMethodField()
    )  # needed to materialize the FK relationship for wagtailimages
    orcid_url = serializers.ReadOnlyField()
    github_url = serializers.ReadOnlyField()
    tags = TagSerializer(many=True)
    profile_url = serializers.URLField(source="get_absolute_url", read_only=True)
    bio = MarkdownField()
    research_interests = MarkdownField()
    peer_reviewer_id = serializers.IntegerField(
        source="peer_reviewer.id", read_only=True, allow_null=True, default=None
    )

    def validate_affiliations(self, value):
        return validate_affiliations(value)

    def get_email(self, instance):
        request = self.context.get("request")
        if request and request.user.is_anonymous:
            return None
        else:
            return instance.email

    def get_avatar(self, instance):
        request = self.context.get("request")
        if request and request.accepted_media_type != "text/html":
            return (
                instance.picture.get_rendition("fill-150x150").url
                if instance.picture
                else None
            )
        return instance.picture

    def save_email(self, user, new_email):
        if user.email != new_email:
            try:
                validate_email(new_email)
                # Check if any user other the user currently being edited has an email account with the same address as the
                # new email
                users_with_email = MemberProfile.objects.find_users_with_email(
                    new_email, exclude_user=user
                )
                if users_with_email.exists():
                    logger.warning(
                        "Unable to register email %s, already owned by [%s]",
                        user.email,
                        users_with_email,
                    )
                    raise DrfValidationError(
                        {"email": ["This email address is already taken."]}
                    )
            except ValidationError as e:
                raise DrfValidationError({"email": e.messages})

            request = self.context.get("request")

            if EmailAddress.objects.filter(primary=True, user=user).exists():
                EmailAddress.objects.add_new_email(request, user, new_email)
            else:
                email_address = EmailAddress.objects.create(
                    primary=True, user=user, email=new_email
                )
                email_address.send_confirmation(request)

            logger.warning(
                "email change for user [pk: %s] %s -> %s, awaiting confirmation.",
                user.id,
                user.email,
                new_email,
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        raw_tags = TagSerializer(many=True, data=validated_data.pop("tags"))
        user = instance.user
        raw_user = validated_data.pop("user")
        user.first_name = raw_user["first_name"]
        user.last_name = raw_user["last_name"]
        user.save()

        new_email = self.initial_data["email"]

        # Full members cannot downgrade their status
        if instance.full_member:
            validated_data["full_member"] = True
        else:
            validated_data["full_member"] = bool(self.initial_data["full_member"])

        logger.debug("validated data in member profile serializer: %s", validated_data)

        obj = super().update(instance, validated_data)
        self.save_tags(instance, raw_tags)
        self.save_email(user, new_email)
        return obj

    @staticmethod
    def save_tags(instance, tags):
        if not tags.is_valid():
            raise serializers.ValidationError(tags.errors)
        db_tags = tags.save()
        instance.tags.clear()
        instance.tags.add(*db_tags)
        instance.save()

    class Meta:
        model = MemberProfile
        fields = (
            # User
            "id",
            "date_joined",
            "family_name",
            "given_name",
            "profile_url",
            "username",
            "email",
            "user_pk",
            # Follower
            "follower_count",
            "following_count",
            "industry",
            # MemberProfile
            "avatar",
            "bio",
            "name",
            "degrees",
            "full_member",
            "tags",
            "orcid_url",
            "github_url",
            "personal_url",
            "professional_url",
            "profile_url",
            "research_interests",
            "affiliations",
            "name",
            "peer_reviewer_id",
        )


class RelatedMemberProfileSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    family_name = serializers.CharField(allow_blank=True, source="user.last_name")
    given_name = serializers.CharField(allow_blank=True, source="user.first_name")

    class Meta:
        model = MemberProfile
        fields = (
            "id",
            "avatar_url",
            "degrees",
            "given_name",
            "family_name",
            "name",
            "email",
            "profile_url",
            "primary_affiliation_name",
            "affiliations",
            "tags",
            "username",
        )


class RelatedUserSerializer(serializers.ModelSerializer):
    member_profile = RelatedMemberProfileSerializer(read_only=True)
    username = serializers.CharField()

    class Meta:
        model = User
        fields = ("id", "username", "member_profile")


class IsoDateField(serializers.DateField):
    """
    Extension to DateField that accepts full ISO 8601 date-time strings
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", [ISO_DATETIME_FORMAT, "iso-8601"])
        super().__init__(*args, **kwargs)


class EventSerializer(serializers.ModelSerializer, SpamCatcherSerializerMixin):
    submitter = RelatedUserSerializer(
        read_only=True, help_text=_("User that created the event"), label="Submitter"
    )
    absolute_url = serializers.URLField(
        source="get_absolute_url",
        read_only=True,
        help_text=_("URL to the detail page of the event"),
    )
    date_created = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    start_date = IsoDateField()
    end_date = IsoDateField(allow_null=True, required=False)
    early_registration_deadline = IsoDateField(allow_null=True, required=False)
    registration_deadline = IsoDateField(allow_null=True, required=False)
    submission_deadline = IsoDateField(allow_null=True, required=False)
    description = MarkdownField()
    is_expired = serializers.BooleanField(read_only=True)
    is_started = serializers.BooleanField(read_only=True)
    is_marked_spam = serializers.BooleanField(read_only=True)

    tags = TagSerializer(many=True, label="Tags")

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        date_created = attrs.get("date_created", timezone.now())
        early_registration_deadline_name = "early_registration_deadline"
        early_registration_deadline = attrs.get(early_registration_deadline_name)
        registration_deadline_name = "registration_deadline"
        registration_deadline = attrs.get(registration_deadline_name)
        submission_deadline_name = "submission_deadline"
        submission_deadline = attrs.get(submission_deadline_name)
        start_date = attrs["start_date"]
        end_date = attrs.get("end_date")

        dates = [date_created]
        if early_registration_deadline:
            dates.append(early_registration_deadline)
        if submission_deadline:
            dates.append(submission_deadline)
        dates.append(start_date)
        if end_date:
            dates.append(end_date)

        msgs = []

        if end_date and start_date >= end_date:
            msgs.append(
                "The event start date should be earlier than the event end date."
            )

        if not end_date:
            end_date = start_date

        if (
            early_registration_deadline
            and registration_deadline
            and registration_deadline < early_registration_deadline
        ):
            msgs.append(
                "Early registration deadlines should be earlier than the regular registration deadline."
            )

        if early_registration_deadline and early_registration_deadline > start_date:
            msgs.append(
                "Early registration deadlines should be earlier than the event start date."
            )

        if registration_deadline and registration_deadline > end_date:
            msgs.append(
                "Registration deadline should be before the event end date (or start date if event is only one day)."
            )

        if submission_deadline and submission_deadline > end_date:
            msgs.append(
                "Submission deadline should be before the event end date (or start date if event is only one day)."
            )

        if msgs:
            raise ValidationError(" ".join(s.capitalize() for s in msgs))

        return attrs

    class Meta:
        model = Event
        fields = "__all__"


class EventCalendarSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(source="start_date")
    end = serializers.DateTimeField(source="end_date")

    class Meta:
        model = Event
        fields = (
            "title",
            "start",
            "end",
        )


class JobSerializer(serializers.ModelSerializer, SpamCatcherSerializerMixin):
    submitter = RelatedUserSerializer(
        read_only=True,
        help_text=_("User that created the job description"),
        label="Submitter",
    )
    absolute_url = serializers.URLField(
        source="get_absolute_url",
        read_only=True,
        help_text=_("URL to the detail page of the job"),
    )

    date_created = serializers.DateTimeField(
        format=DATE_PUBLISHED_FORMAT, read_only=True
    )
    description = MarkdownField()
    is_expired = serializers.BooleanField(read_only=True)
    is_marked_spam = serializers.BooleanField(read_only=True)
    last_modified = serializers.DateTimeField(read_only=True)
    application_deadline = IsoDateField(allow_null=True, required=False)
    tags = TagSerializer(many=True, label="Tags")

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "submitter",
            "date_created",
            "last_modified",
            "application_deadline",
            "description",
            "summary",
            "absolute_url",
            "tags",
            "external_url",
            "is_expired",
            "is_deleted",
            "is_marked_spam",
        )
