import logging

from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from markupfield.fields import Markup
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from taggit.models import Tag

from .models import Event, Job, Institution

logger = logging.getLogger(__name__)

YMD_DATETIME_FORMAT = "%Y-%m-%d"
DATE_PUBLISHED_FORMAT = "%b %d, %Y"
FULL_DATE_FORMAT = "%A, %B %d, %Y"


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


class LinkedUserSerializer(serializers.ModelSerializer):
    profile_url = serializers.URLField(
        source="member_profile.get_absolute_url", read_only=True
    )
    name = serializers.SerializerMethodField()
    username = serializers.ReadOnlyField()

    def get_name(self, user):
        # FIXME: duplicate logic in user.member_profile.name
        return user.get_full_name() or user.username

    class Meta:
        model = User
        fields = ("name", "profile_url", "username")


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


class EventSerializer(serializers.ModelSerializer):
    submitter = LinkedUserSerializer(
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
    description = MarkdownField()
    expired = serializers.BooleanField(read_only=True)

    tags = TagSerializer(many=True, label="Tags")

    def create(self, validated_data):
        return create(self.Meta.model, validated_data, self.context)

    def update(self, instance, validated_data):
        return update(super().update, instance, validated_data)

    def validate(self, attrs):
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


class JobSerializer(serializers.ModelSerializer):
    submitter = LinkedUserSerializer(
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
    last_modified = serializers.DateTimeField(format="%c", read_only=True)
    application_deadline = serializers.DateField(
        allow_null=True, input_formats=["%Y-%m-%dT%H:%M:%S.%fZ", "iso-8601"]
    )
    formatted_application_deadline = serializers.DateField(
        source="application_deadline", read_only=True, format=DATE_PUBLISHED_FORMAT
    )
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
            "formatted_application_deadline",
            "description",
            "summary",
            "absolute_url",
            "tags",
            "external_url",
        )


class InstitutionSerializer(serializers.ModelSerializer):
    # Not sure why these need required and allow blank, should have correct defaults
    # from blank=True in the model
    name = serializers.CharField(allow_blank=False)
    url = serializers.URLField(required=False, allow_blank=True)
    acronym = serializers.CharField(required=False, allow_blank=True)
    ror_id = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Institution
        fields = (
            "name",
            "url",
            "acronym",
            "ror_id",
        )
