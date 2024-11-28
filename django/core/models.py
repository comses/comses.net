import logging
import pathlib
from datetime import timedelta
from enum import Enum

from allauth.account.models import EmailAddress
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TaggedItemBase
from timezone_field import TimeZoneField
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.images.models import Image
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .backends import add_to_comses_permission_whitelist
from .discourse import sanitize_username
from .fields import MarkdownField

EXCLUDED_USERNAMES = ("AnonymousUser", "openabm")


logger = logging.getLogger(__name__)


class ComsesGroups(Enum):
    ADMIN = "Admins"
    MODERATOR = "Moderators"
    EDITOR = "Editors"
    FULL_MEMBER = "Full Members"

    @staticmethod
    @transaction.atomic
    def initialize():
        return [Group.objects.get_or_create(name=g.value)[0] for g in ComsesGroups]

    def users(self, **kwargs):
        kwargs.setdefault("is_active", True)
        return self.get_group().user_set.filter(**kwargs)

    def member_profiles(self, **kwargs):
        return MemberProfile.objects.filter(user__in=self.users(**kwargs))

    def get_group(self):
        _group = getattr(self, "group", None)
        if _group is None:
            _group = self.group = Group.objects.get(name=self.value)
        return _group

    def is_member(self, user):
        return ComsesGroups.is_group_member(user, self.value)

    def set_membership(self, user: User, value: bool):
        """
        Add or remove a user from this Group

        Parameters:
        - user (User): The user to add or remove from the group.
        - value (bool): set to True to add, False to remove
        """
        if value:
            self.add(user)
        else:
            self.remove(user)

    def add(self, user):
        user.groups.add(Group.objects.get(name=self.value))

    def remove(self, user):
        user.groups.remove(Group.objects.get(name=self.value))

    @staticmethod
    def is_moderator(user):
        return ComsesGroups.MODERATOR.is_member(user)

    @staticmethod
    def is_full_member(user):
        return ComsesGroups.FULL_MEMBER.is_member(user)

    @staticmethod
    def is_group_member(user, group_name: str):
        if group_name:
            return user.groups.filter(name=group_name).exists()
        return False


def get_sentinel_user():
    return get_user_model().get_anonymous()


@register_setting
class SiteSettings(BaseSiteSetting):
    maintenance_mode = models.BooleanField(default=False)
    banner_message_title = models.CharField(
        max_length=64, blank=True, default="CoMSES Net Notice"
    )
    banner_message = MarkdownField(
        help_text=_("Markdown-enabled banner notification displayed on the front page"),
        blank=True,
    )
    banner_destination_url = models.URLField(
        help_text=_("URL to redirect to when this banner is clicked"), blank=True
    )
    # expired_event_days_threshold = models.PositiveIntegerField(default=3, help_text=_("Number of days after an event's start date for which an event will be considered expired.")
    last_modified = models.DateTimeField(auto_now=True)
    mailchimp_digest_archive_url = models.URLField(
        help_text=_("Mailchimp Digest Campaign Archive URL"), blank=True
    )

    @property
    def has_banner(self):
        return bool(self.banner_message.raw.strip())

    def is_production(self):
        return settings.DEPLOY_ENVIRONMENT.is_production

    def deploy_environment(self):
        return settings.DEPLOY_ENVIRONMENT


class SpamModeration(models.Model):
    class Status(models.TextChoices):
        SPAM = "spam", _("Confirmed spam")
        NOT_SPAM = "not_spam", _("Confirmed not spam")
        SCHEDULED_FOR_CHECK = "scheduled_for_check", _("Scheduled for check by LLM")
        SPAM_LIKELY = "spam_likely", _("Automatically marked as spam")
        NOT_SPAM_LIKELY = "not_spam_likely", _("Automatically marked as not spam")

    status = models.CharField(
        choices=Status.choices,
        default=Status.SCHEDULED_FOR_CHECK,
        max_length=32,
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    notes = models.TextField(
        blank=True, null=True, help_text=_("Additional notes left by the reviewer")
    )
    # FIXME: should we start an enum / choices for this?
    detection_method = models.CharField(max_length=255, blank=True, null=True)
    detection_details = models.JSONField(
        default=dict,
        help_text=_(
            "Extra context from the detection method, e.g. NLP results, elapsed time"
        ),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        null=True,
        blank=True,
    )

    # detection_details is a JSON field
    def mark_as_spam_by_llm(self, status: Status, detection_details=None):
        logger.info("Marking %s as %s by LLM", self, status)
        self.reviewer = None
        self.status = status
        self.detection_method = "LLM"
        if detection_details:
            self.detection_details = detection_details
        self.save()

    def mark_not_spam(self, reviewer: User, detection_details=None):
        logger.info("user %s marking %s as not spam", reviewer, self)
        self.status = self.Status.NOT_SPAM
        self.reviewer = reviewer
        if detection_details:
            self.detection_details = detection_details
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_related_object()

    def update_related_object(self):
        related_object = self.content_object
        if hasattr(related_object, "is_marked_spam"):
            related_object.spam_moderation = self
            related_object.is_marked_spam = self.status in {
                self.Status.SPAM,
                self.Status.SPAM_LIKELY,
            }
            related_object.save()

    def __str__(self):
        return (
            f"SpamModeration: {self.status} - {self.reviewer} - {self.content_object}"
        )


class ModeratedContent(models.Model):
    spam_moderation = models.ForeignKey(
        SpamModeration, null=True, blank=True, on_delete=models.SET_NULL
    )
    # need to have this denormalized field to allow for filtering out spam content
    # https://docs.wagtail.org/en/stable/topics/search/indexing.html#filtering-on-index-relatedfields
    is_marked_spam = models.BooleanField(
        default=False,
        help_text=_(
            "cached boolean representation of spam_moderation for search indexing"
        ),
    )

    def mark_not_spam(self, user: User):
        """
        Clear spam status for this object
        """
        if self.spam_moderation:
            self.spam_moderation.mark_not_spam(user)

    def mark_spam(self, status=SpamModeration.Status.SPAM, **kwargs):
        content_type = ContentType.objects.get_for_model(type(self))
        self.spam_moderation, created = SpamModeration.objects.get_or_create(
            status=status,
            object_id=self.id,
            content_type=content_type,
            **kwargs,
        )

    class Meta:
        abstract = True


@register_setting
class SocialMediaSettings(BaseSiteSetting):
    facebook_url = models.URLField(help_text=_("Facebook URL"), blank=True)
    youtube_url = models.URLField(help_text=_("CoMSES Net YouTube Channel"), blank=True)
    twitter_account = models.CharField(
        max_length=128,
        default="comses",
        help_text=_("CoMSES Net official Twitter account"),
        blank=True,
    )
    github_account = models.CharField(
        max_length=128,
        default="comses",
        help_text=_("CoMSES Net official GitHub account"),
        blank=True,
    )
    mailing_list_url = models.URLField(
        help_text=_("Mailing List Signup URL, i.e., MailChimp signup form"), blank=True
    )
    contact_form_recipients = ArrayField(
        models.EmailField(),
        help_text=_(
            "Email address(es) where contact forms will be sent. Separate multiple addresses with commas,"
            " e.g., `editors@comses.net,info@comses.net`"
        ),
        default=list,
    )


@register_snippet
class Institution(models.Model):
    # FIXME: institution deprecated in favor of affiliations, consider removal
    name = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    acronym = models.CharField(max_length=50, blank=True)
    ror_id = models.URLField(blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
        FieldPanel("acronym"),
        FieldPanel("ror_id"),
    ]

    def __str__(self):
        return f"{self.name} {self.ror_id}"


class MemberProfileTag(TaggedItemBase):
    content_object = ParentalKey("core.MemberProfile", related_name="tagged_members")


class FollowUser(models.Model):
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers", on_delete=models.CASCADE
    )
    source = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="following", on_delete=models.CASCADE
    )

    def __str__(self):
        return "{0} following {1}".format(self.source, self.target)


class MemberProfileQuerySet(models.QuerySet):
    def find_by_name(self, query):
        return self.filter(
            models.Q(user__username__icontains=query)
            | models.Q(user__last_name__icontains=query)
            | models.Q(user__first_name__icontains=query)
            | models.Q(user__contributor__given_name__icontains=query)
            | models.Q(user__contributor__family_name__icontains=query)
        )

    def with_peer_review_invitations(self):
        return self.prefetch_related("user").prefetch_related(
            "peer_review_invitation_set__review__codebase_release__codebase"
        )

    def with_user(self):
        return self.select_related("user")

    def with_tags(self):
        return self.prefetch_related("tagged_members__tag")

    def full_members(self, **kwargs):
        return ComsesGroups.FULL_MEMBER.member_profiles(**kwargs)

    def editors(self, **kwargs):
        return ComsesGroups.EDITOR.member_profiles(**kwargs)

    def public(self, **kwargs):
        return self.filter(user__is_active=True, **kwargs).exclude(
            user__username__in=EXCLUDED_USERNAMES
        )

    def with_affiliations(self, **kwargs):
        return self.exclude(affiliations=[]).filter(**kwargs)

    def find_users_with_email(self, candidate_email, exclude_user=None):
        """
        Return a queryset of user ids with the given email
        """
        if exclude_user is None:
            exclude_user = User.get_anonymous()
        return (
            EmailAddress.objects.filter(email=candidate_email)
            .exclude(user=exclude_user)
            .values_list("user")
            .union(
                User.objects.filter(email=candidate_email)
                .exclude(id=exclude_user.id)
                .values_list("id")
            )
        )


@add_to_comses_permission_whitelist
@register_snippet
class MemberProfile(index.Indexed, ModeratedContent, ClusterableModel):
    """
    Contains additional comses.net information, possibly linked to a CoMSES Member / site account
    """

    class Industry(models.TextChoices):
        COLLEGE_UNIVERSITY = "university", _("College/University")
        EDUCATOR = "educator", _("K-12 Educator")
        GOVERNMENT = "government", _("Government")
        PRIVATE = "private", _("Private")
        NON_PROFIT = "nonprofit", _("Non-Profit")
        STUDENT = "student", _("Student")
        OTHER = "other", _("Other")

    user = models.OneToOneField(
        User, null=True, on_delete=models.CASCADE, related_name="member_profile"
    )

    # FIXME: add location field eventually, with postgis
    # location = LocationField(based_fields=['city'], zoom=7)

    timezone = TimeZoneField(blank=True)
    industry = models.CharField(blank=True, max_length=255, choices=Industry.choices)
    bio = MarkdownField(max_length=2048, help_text=_("Brief bio"))
    degrees = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    # FIXME: institution deprecated in favor of affiliations, consider removal
    institution = models.ForeignKey(Institution, null=True, on_delete=models.SET_NULL)
    # user's institutional affiliations
    affiliations = models.JSONField(
        default=list, help_text=_("JSON-LD list of affiliated institutions")
    )
    tags = ClusterTaggableManager(through=MemberProfileTag, blank=True)

    personal_url = models.URLField(blank=True)
    picture = models.ForeignKey(
        Image, null=True, help_text=_("Profile picture"), on_delete=models.SET_NULL
    )
    professional_url = models.URLField(blank=True)
    research_interests = MarkdownField(max_length=2048)
    short_uuid = models.CharField(max_length=32, unique=True, null=True)

    objects = MemberProfileQuerySet.as_manager()

    panels = [
        FieldPanel("bio", widget=forms.Textarea),
        FieldPanel("research_interests", widget=forms.Textarea),
        FieldPanel("personal_url"),
        FieldPanel("professional_url"),
        FieldPanel("affiliations"),
        FieldPanel("industry"),
        FieldPanel("picture"),
        FieldPanel("tags"),
    ]

    search_fields = [
        index.FilterField("date_joined"),
        index.FilterField("is_active"),
        index.FilterField("username"),
        index.SearchField("affiliations_string"),
        index.SearchField("bio"),
        index.SearchField("degrees"),
        index.SearchField("email"),
        index.SearchField("name"),
        index.SearchField("research_interests"),
        index.RelatedFields(
            "tags",
            [
                # FilterFields do not currently work but should be supported in a future wagtail release
                # https://docs.wagtail.org/en/stable/topics/search/indexing.html#filtering-on-index-relatedfields
                index.FilterField("name"),
            ],
        ),
    ]

    # Proxies to related user object

    @property
    def date_joined(self):
        return self.user.date_joined

    @property
    def email(self):
        return self.user.email

    @property
    def username(self):
        return self.user.username

    @property
    def discourse_username(self):
        return sanitize_username(self.username, uid=self.short_uuid)

    @property
    def is_active(self):
        return self.user.is_active

    @property
    def is_reviewer(self):
        return hasattr(self, "peer_reviewer")

    # Urls
    @property
    def orcid_url(self):
        """
        Returns the ORCID profile URL associated with this member profile if it exists, or None
        """
        return self.get_social_account_profile_url("orcid")

    @property
    def avatar_url(self):
        if self.picture:
            return self.picture.get_rendition("fill-150x150").url
        return None

    @property
    def github_url(self):
        """
        Returns the github profile URL associated with this member profile if it exists, or None
        """
        return self.get_social_account_profile_url("github")

    def get_social_account_profile_url(self, provider_name):
        social_acct = self.get_social_account(provider_name)
        if social_acct:
            return social_acct.get_profile_url()
        return None

    def get_social_account(self, provider_name):
        return self.user.socialaccount_set.filter(provider=provider_name).first()

    @property
    def primary_affiliation_url(self):
        return self.affiliations[0].get("url") if self.affiliations else ""

    @cached_property
    def affiliations_string(self):
        return ", ".join(
            [
                self.to_affiliation_string(affiliation)
                for affiliation in self.affiliations
            ]
        )

    @property
    def profile_url(self):
        return self.get_absolute_url()

    def get_absolute_url(self):
        return reverse("core:profile-detail", kwargs={"pk": self.user.id})

    def get_edit_url(self):
        return reverse("core:profile-edit", kwargs={"user__pk": self.user.id})

    @classmethod
    def get_list_url(cls):
        return reverse("core:profile-list")

    @classmethod
    def to_affiliation_string(cls, afl):
        # e.g., "Arizona State University https://www.asu.edu ASU"
        return f"{afl.get('name')} {afl.get('url')} {afl.get('acronym')}"

    @cached_property
    def primary_affiliation_name(self):
        """
        Primary affiliation is always first
        """
        return self.affiliations[0].get("name") if self.affiliations else ""

    @property
    def submitter(self):
        return self.user

    @cached_property
    def name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def full_member(self):
        return ComsesGroups.is_full_member(self.user)

    @full_member.setter
    def full_member(self, value):
        ComsesGroups.FULL_MEMBER.set_membership(self.user, value)

    def is_messageable(self, user):
        return user.is_authenticated and user != self.user

    def get_download_request_metadata(self):
        """Returns a dictionary of metadata to be included in the download request modal form if available"""
        user_metadata = {
            "authenticated": self.user.is_authenticated,
            "industry": self.industry,
            "id": self.user.id,
        }
        if self.affiliations:
            user_metadata["affiliation"] = self.affiliations[0]
        return user_metadata

    @classmethod
    def get_indexed_objects(cls):
        return cls.objects.public()

    def __str__(self):
        return str(self.user)


class PlatformTag(TaggedItemBase):
    content_object = ParentalKey("core.Platform", related_name="tagged_platforms")


@register_snippet
class Platform(index.Indexed, ClusterableModel):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    description = MarkdownField(max_length=1024)
    date_created = models.DateTimeField(default=timezone.now)
    # last_updated = models.DateField(blank=True, null=True, help_text=_("Date of last update for the ABM platform itself."))
    last_modified = models.DateTimeField(auto_now=True)
    open_source = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    tags = ClusterTaggableManager(through=PlatformTag, blank=True)

    @staticmethod
    def _upload_path(instance, filename):
        # FIXME: base in MEDIA_ROOT?
        return pathlib.Path("platforms", instance.platform.name, filename)

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
        FieldPanel("description"),
        FieldPanel("active"),
        FieldPanel("open_source"),
        FieldPanel("featured"),
        FieldPanel("tags"),
    ]

    def get_all_tags(self):
        return " ".join(self.tags.all().values_list("name", flat=True))

    search_fields = [
        index.SearchField("name"),
        index.SearchField("description"),
        index.FilterField("active"),
        index.FilterField("open_source"),
        index.FilterField("featured"),
        index.RelatedFields(
            "tags",
            [
                index.FilterField("name"),
            ],
        ),
    ]

    def __str__(self):
        return self.name

    def __lt__(self, other):
        if isinstance(other, Platform):
            return self.name < other.name
        raise TypeError("Unorderable types: {0} < {1}".format(Platform, type(other)))


class PlatformRelease(models.Model):
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    version = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    archive = models.FileField(upload_to=Platform._upload_path, null=True)


class EventTag(TaggedItemBase):
    content_object = ParentalKey("core.Event", related_name="tagged_events")


class EventQuerySet(models.QuerySet):
    def find_by_interval(self, start, end):
        """
        Returns all Events whose early registration deadline or submission deadline falls within the interval and whose
        start date and end date intersect with the interval
        :param start:
        :param end:
        :return:
        """
        return self.filter(
            # early registration deadline falls between the interval
            models.Q(early_registration_deadline__range=[start, end])
            |
            # or submission deadline falls between the interval
            models.Q(submission_deadline__range=[start, end])
            | models.Q(start_date__range=[start, end])
            | models.Q(end_date__range=[start, end])
        )

    def with_submitter(self):
        return self.select_related("submitter")

    def with_tags(self):
        return self.prefetch_related("tagged_events__tag")

    def with_expired(self):
        return self.annotate(
            is_expired=models.ExpressionWrapper(
                self.get_expired_q(),
                output_field=models.BooleanField(),
            )
        )

    def with_started(self):
        return self.annotate(
            is_started=models.ExpressionWrapper(
                models.Q(start_date__gt=timezone.now().date()),
                output_field=models.BooleanField(),
            )
        )

    def upcoming(self, **kwargs):
        """returns only events that have not expired"""
        return self.filter(
            ~self.get_expired_q(),
            **kwargs,
        )

    def get_expired_q(self):
        """
        returns a Q object for all events with that have not yet ended or
        started less than 2 days ago
        """
        now = timezone.now().date()
        start_date_threshold = now - timedelta(
            days=settings.EXPIRED_EVENT_DAYS_THRESHOLD
        )
        return models.Q(start_date__lt=start_date_threshold) | models.Q(
            end_date__lt=now, end_date__isnull=False
        )

    def live(self, **kwargs):
        return self.filter(is_deleted=False, **kwargs)

    def exclude_spam(self):
        # FIXME: duplicated across Event/Job/Codebase querysets
        return self.exclude(is_marked_spam=True)

    def latest_for_feed(self, number=10):
        return (
            self.live()
            .select_related("submitter__member_profile")
            .order_by("-date_created")[:number]
        )

    def public(self):
        return self.filter(is_deleted=False).exclude_spam()


@add_to_comses_permission_whitelist
class Event(index.Indexed, ModeratedContent, ClusterableModel):
    title = models.CharField(max_length=300)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True)
    description = MarkdownField()
    early_registration_deadline = models.DateField(null=True, blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    submission_deadline = models.DateField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=300)
    tags = ClusterTaggableManager(through=EventTag, blank=True)
    external_url = models.URLField(blank=True)
    is_deleted = models.BooleanField(default=False)
    objects = EventQuerySet.as_manager()

    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user), blank=True
    )

    search_fields = [
        index.SearchField("title"),
        index.SearchField("description"),
        index.FilterField("is_marked_spam"),
        index.FilterField("is_deleted"),
        index.FilterField("date_created"),
        index.FilterField("start_date"),
        index.FilterField("end_date"),
        index.FilterField("last_modified"),
        index.FilterField("submission_deadline"),
        index.FilterField("early_registration_deadline"),
        index.FilterField("registration_deadline"),
        index.SearchField("location"),
        index.RelatedFields(
            "tags",
            [
                index.SearchField("name"),
            ],
        ),
        index.RelatedFields(
            "submitter",
            [
                index.SearchField("username"),
                index.SearchField("email"),
                index.SearchField("get_full_name"),
            ],
        ),
    ]

    @property
    def live(self):
        return not self.is_deleted

    def get_absolute_url(self):
        return reverse("core:event-detail", kwargs={"pk": self.id})

    @classmethod
    def get_list_url(cls):
        return reverse("core:event-list")

    @classmethod
    def get_indexed_objects(cls):
        return cls.objects.public()

    def __str__(self):
        return "{0} posted by {1} on {2}".format(
            self.title, self.submitter.username, self.date_created.strftime("%c")
        )


class JobTag(TaggedItemBase):
    content_object = ParentalKey("core.Job", related_name="tagged_jobs")


class JobQuerySet(models.QuerySet):
    def with_submitter(self):
        return self.select_related("submitter")

    def with_tags(self):
        return self.prefetch_related("tagged_jobs__tag")

    def public(self):
        return self.filter(is_deleted=False).exclude_spam()

    def with_expired(self):
        return self.annotate(
            is_expired=models.ExpressionWrapper(
                self.get_expired_q(),
                output_field=models.BooleanField(),
            ),
        )

    def upcoming(self, **kwargs):
        """returns only jobs that have not expired"""
        return self.filter(
            ~self.get_expired_q(),
            **kwargs,
        )

    def get_expired_q(self):
        """
        returns a Q object for all Jobs with a non-null application deadline before today or
        posted/modified in the last [settings.EXPIRED_JOB_DAYS_THRESHOLD] days if
        application deadline is null
        """
        today = timezone.now()
        threshold = settings.EXPIRED_JOB_DAYS_THRESHOLD
        post_date_threshold = today - timedelta(days=threshold)
        return models.Q(
            application_deadline__isnull=False, application_deadline__lt=today
        ) | models.Q(
            application_deadline__isnull=True,
            date_created__lt=post_date_threshold,
            last_modified__lt=post_date_threshold,
        )

    def live(self, **kwargs):
        return self.filter(is_deleted=False, **kwargs)

    def exclude_spam(self):
        # FIXME: duplicated across Event/Job/Codebase querysets
        return self.exclude(is_marked_spam=True)

    def latest_for_feed(self, number=10):
        return (
            self.live()
            .select_related("submitter__member_profile")
            .order_by("-date_created")[:number]
        )


@add_to_comses_permission_whitelist
class Job(index.Indexed, ModeratedContent, ClusterableModel):
    title = models.CharField(max_length=300, help_text=_("Job posting title"))
    date_created = models.DateTimeField(default=timezone.now)
    application_deadline = models.DateField(
        blank=True, null=True, help_text=_("Optional deadline for applications")
    )
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(
        max_length=500, blank=True, help_text=_("Brief summary of job posting.")
    )
    description = MarkdownField()
    tags = ClusterTaggableManager(through=JobTag, blank=True)
    external_url = models.URLField(blank=True)
    is_deleted = models.BooleanField(default=False)

    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="jobs",
        on_delete=models.SET(get_sentinel_user),
    )

    objects = JobQuerySet.as_manager()

    search_fields = [
        index.SearchField("title"),
        index.SearchField("description"),
        index.FilterField("is_marked_spam"),
        index.FilterField("is_deleted"),
        index.FilterField("date_created"),
        index.FilterField("last_modified"),
        index.FilterField("application_deadline"),
        index.RelatedFields(
            "tags",
            [
                index.SearchField("name"),
            ],
        ),
        index.RelatedFields(
            "submitter",
            [
                index.SearchField("username"),
                index.SearchField("email"),
                index.SearchField("get_full_name"),
            ],
        ),
    ]

    @property
    def live(self):
        return not self.is_deleted

    def get_absolute_url(self):
        return reverse("core:job-detail", kwargs={"pk": self.id})

    @classmethod
    def get_list_url(cls):
        return reverse("core:job-list")

    @classmethod
    def get_indexed_objects(cls):
        return cls.objects.public()

    def __str__(self):
        return "{0} posted by {1} on {2}".format(
            self.title, self.submitter.username, self.date_created.strftime("%c")
        )

    @property
    def owner(self):
        return self.submitter
