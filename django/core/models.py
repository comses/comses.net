import pathlib

from allauth.account.models import EmailAddress
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from enum import Enum
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TaggedItemBase
from timezone_field import TimeZoneField
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.settings.models import BaseSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import Image
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .backends import add_to_comses_permission_whitelist
from .fields import MarkdownField

EXCLUDED_USERNAMES = ('AnonymousUser', 'openabm')


class ComsesGroups(Enum):
    ADMIN = "Admins"
    EDITOR = "Editors"
    FULL_MEMBER = "Full Members"
    REVIEWER = "Reviewers"

    @staticmethod
    def initialize():
        return [Group.objects.get_or_create(name=g.value)[0] for g in ComsesGroups]

    def get_group(self):
        _group = getattr(self, 'group', None)
        if _group is None:
            _group = self.group = Group.objects.get(name=self.value)
        return _group


@transaction.atomic
def get_sentinel_user():
    return get_user_model().objects.get_or_create(username='openabm')[0]


@register_setting
class SiteSettings(BaseSetting):
    maintenance_mode = models.BooleanField(default=False)

    def is_production(self):
        return settings.DEPLOY_ENVIRONMENT.is_production()

    def deploy_environment(self):
        return settings.DEPLOY_ENVIRONMENT


@register_setting
class SocialMediaSettings(BaseSetting):
    facebook_url = models.URLField(help_text=_('Facebook URL'), blank=True)
    youtube_url = models.URLField(help_text=_('CoMSES Net YouTube Channel'), blank=True)
    twitter_account = models.CharField(max_length=128, default='comses',
                                       help_text=_('CoMSES Net official Twitter account'), blank=True)
    github_account = models.CharField(max_length=128, default='comses',
                                      help_text=_('CoMSES Net official GitHub account'), blank=True)
    mailing_list_url = models.URLField(help_text=_('Mailing List Signup URL, i.e., MailChimp signup form'), blank=True)
    contact_form_recipients = ArrayField(
        models.EmailField(),
        help_text=_('Email address(es) where contact forms will be sent. Separate multiple addresses with commas,'
                    ' e.g., `editors@comses.net,info@comses.net`'),
        default=list)


@register_snippet
class Institution(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    acronym = models.CharField(max_length=50)

    content_panels = [
        FieldPanel('name'),
        FieldPanel('url'),
        FieldPanel('acronym'),
    ]

    def __str__(self):
        return self.name


class MemberProfileTag(TaggedItemBase):
    content_object = ParentalKey('core.MemberProfile', related_name='tagged_members')


class FollowUser(models.Model):
    target = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='followers', on_delete=models.CASCADE)
    source = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following', on_delete=models.CASCADE)

    def __str__(self):
        return '{0} following {1}'.format(self.source, self.target)


class MemberProfileQuerySet(models.QuerySet):

    def find_by_name(self, query):
        return self.filter(models.Q(user__username__icontains=query) |
                           models.Q(user__last_name__icontains=query) |
                           models.Q(user__first_name__icontains=query) |
                           models.Q(user__contributor__given_name__icontains=query) |
                           models.Q(user__contributor__family_name__icontains=query))

    def with_institution(self):
        return self.select_related('institution')

    def with_user(self):
        return self.select_related('user')

    def with_tags(self):
        return self.prefetch_related('tagged_members__tag')

    def public(self, **kwargs):
        return self.filter(user__is_active=True, **kwargs).exclude(user__username__in=EXCLUDED_USERNAMES)

    def find_users_with_email(self, candidate_email, exclude_user=None):
        """
        Return a queryset of user pks with the given email
        """
        if exclude_user is None:
            exclude_user = User.get_anonymous()
        return EmailAddress.objects.filter(email=candidate_email).exclude(user=exclude_user).values_list('user').union(
            User.objects.filter(email=candidate_email).exclude(pk=exclude_user.pk).values_list('pk'))


@add_to_comses_permission_whitelist
@register_snippet
class MemberProfile(index.Indexed, ClusterableModel):
    """
    Contains additional comses.net information, possibly linked to a CoMSES Member / site account
    """

    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL, related_name='member_profile')

    # FIXME: add location field eventually, with postgis
    # location = LocationField(based_fields=['city'], zoom=7)

    timezone = TimeZoneField(blank=True)

    affiliations = JSONField(default=list, help_text=_("JSON-LD list of affiliated institutions"))
    bio = MarkdownField(max_length=512, help_text=_('Brief bio'))
    degrees = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    institution = models.ForeignKey(Institution, null=True, on_delete=models.SET_NULL)
    tags = ClusterTaggableManager(through=MemberProfileTag, blank=True)

    personal_url = models.URLField(blank=True)
    picture = models.ForeignKey(Image, null=True, help_text=_('Profile picture'), on_delete=models.SET_NULL)
    professional_url = models.URLField(blank=True)
    research_interests = MarkdownField(max_length=512)

    objects = MemberProfileQuerySet.as_manager()

    panels = [
        FieldPanel('bio', widget=forms.Textarea),
        FieldPanel('research_interests', widget=forms.Textarea),
        FieldPanel('personal_url'),
        FieldPanel('professional_url'),
        FieldPanel('institution'),
        ImageChooserPanel('picture'),
        FieldPanel('tags'),
    ]

    search_fields = [
        index.SearchField('bio', partial_match=True, boost=5),
        index.SearchField('research_interests', partial_match=True, boost=5),
        index.FilterField('is_active'),
        index.FilterField('username'),
        index.SearchField('degrees', partial_match=True),
        index.SearchField('name', partial_match=True, boost=5),
        index.RelatedFields('institution', [
            index.SearchField('name', partial_match=True),
        ]),
        index.RelatedFields('tags', [
            index.SearchField('name', partial_match=True),
        ]),
        index.RelatedFields('user', [
            index.SearchField('first_name', partial_match=True),
            index.SearchField('last_name', partial_match=True, boost=3),
            index.SearchField('email', partial_match=True, boost=3)
        ]),
    ]

    """
    Returns the ORCID profile URL associated with this member profile if it exists, or None
    """

    @property
    def orcid_url(self):
        return self.get_social_account_profile_url('orcid')

    @property
    def avatar_url(self):
        if self.picture:
            return self.picture.get_rendition('fill-150x150').url
        return None

    """
    Returns the github profile URL associated with this member profile if it exists, or None
    """

    @property
    def github_url(self):
        return self.get_social_account_profile_url('github')

    def get_social_account_profile_url(self, provider_name):
        social_acct = self.get_social_account(provider_name)
        if social_acct:
            return social_acct.get_profile_url()
        return None

    def get_social_account(self, provider_name):
        return self.user.socialaccount_set.filter(provider=provider_name).first()

    @property
    def institution_name(self):
        return self.institution.name if self.institution else None

    @property
    def institution_url(self):
        return self.institution.url if self.institution else None

    @property
    def submitter(self):
        return self.user

    @property
    def is_active(self):
        return self.user.is_active

    @property
    def is_reviewer(self):
        return self.user.groups.filter(name=ComsesGroups.REVIEWER.value).exists()

    @property
    def username(self):
        return self.user.username

    @property
    def name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def full_member(self):
        return self.user.groups.filter(name=ComsesGroups.FULL_MEMBER.value).exists()

    @full_member.setter
    def full_member(self, value):
        group = Group.objects.get(name=ComsesGroups.FULL_MEMBER.value)
        if value:
            self.user.groups.add(group)
        else:
            self.user.groups.remove(group)

    @property
    def profile_url(self):
        return self.get_absolute_url()

    def get_absolute_url(self):
        return reverse('home:profile-detail', kwargs={'pk': self.user.pk})

    def __str__(self):
        return str(self.user)


class PlatformTag(TaggedItemBase):
    content_object = ParentalKey('core.Platform', related_name='tagged_platforms')


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
    tags = ClusterTaggableManager(through=PlatformTag, blank=True)

    @staticmethod
    def _upload_path(instance, filename):
        # FIXME: base in MEDIA_ROOT?
        return pathlib.Path('platforms', instance.platform.name, filename)

    panels = [
        FieldPanel('name'),
        FieldPanel('url'),
        FieldPanel('description'),
        FieldPanel('active'),
        FieldPanel('open_source'),
        FieldPanel('featured'),
        FieldPanel('tags'),
    ]

    def get_all_tags(self):
        return ' '.join(self.tags.all().values_list('name', flat=True))

    search_fields = [
        index.SearchField('name', partial_match=True),
        index.SearchField('description', partial_match=True),
        index.FilterField('active'),
        index.FilterField('open_source'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
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
    content_object = ParentalKey('core.Event', related_name='tagged_events')


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
            models.Q(early_registration_deadline__range=[start, end]) |
            # or submission deadline falls between the interval
            models.Q(submission_deadline__range=[start, end]) |
            models.Q(start_date__range=[start, end]) |
            models.Q(end_date__range=[start, end])
        )

    def with_submitter(self):
        return self.select_related('submitter')

    def with_tags(self):
        return self.prefetch_related('tagged_events__tag')

    def upcoming(self):
        return self.public().filter(start_date__gte=timezone.now())

    def latest_for_feed(self, number=10):
        return self.select_related('submitter__member_profile').order_by('-date_created')[:number]

    def public(self):
        return self


@add_to_comses_permission_whitelist
class Event(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True)
    description = MarkdownField()
    early_registration_deadline = models.DateTimeField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300)
    tags = ClusterTaggableManager(through=EventTag, blank=True)
    external_url = models.URLField(blank=True)

    objects = EventQuerySet.as_manager()

    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user))

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.FilterField('start_date'),
        index.FilterField('submission_deadline'),
        index.FilterField('early_registration_deadline'),
        index.FilterField('registration_deadline'),
        index.SearchField('location', partial_match=True),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('submitter', [
            index.SearchField('username'),
            index.SearchField('email', partial_match=True),
            index.SearchField('get_full_name', partial_match=True),
        ]),
    ]

    @property
    def live(self):
        return True

    def get_absolute_url(self):
        return reverse('home:event-detail', kwargs={'pk': self.pk})

    @classmethod
    def get_list_url(cls):
        return reverse('home:event-list')

    def __str__(self):
        return "{0} posted by {1} on {2}".format(
            self.title, self.submitter.username, self.date_created.strftime('%c')
        )

    class Meta:
        permissions = (('view_event', 'Can view events'),)


class JobTag(TaggedItemBase):
    content_object = ParentalKey('core.Job', related_name='tagged_jobs')


class JobQuerySet(models.QuerySet):
    def with_submitter(self):
        return self.select_related('submitter')

    def with_tags(self):
        return self.prefetch_related('tagged_jobs__tag')

    def public(self):
        return self

    def latest_for_feed(self, number=10):
        return self.select_related('submitter__member_profile').order_by('-date_created')[:number]


@add_to_comses_permission_whitelist
class Job(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300, help_text=_('Job posting title'))
    date_created = models.DateTimeField(default=timezone.now)
    application_deadline = models.DateField(blank=True, null=True, help_text=_('Optional deadline for applications'))
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True, help_text=_('Brief summary of job posting.'))
    description = MarkdownField()
    tags = ClusterTaggableManager(through=JobTag, blank=True)
    external_url = models.URLField(blank=True)

    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='jobs', on_delete=models.SET(get_sentinel_user))

    objects = JobQuerySet.as_manager()

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.FilterField('date_created'),
        index.FilterField('application_deadline'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('submitter', [
            index.SearchField('username'),
            index.SearchField('email', partial_match=True),
            index.SearchField('get_full_name', partial_match=True),
        ]),
    ]

    @property
    def live(self):
        return True

    def get_absolute_url(self):
        return reverse('home:job-detail', kwargs={'pk': self.pk})

    @classmethod
    def get_list_url(cls):
        return reverse('home:job-list')

    def __str__(self):
        return "{0} posted by {1} on {2}".format(
            self.title, self.submitter.username, self.date_created.strftime('%c')
        )

    @property
    def owner(self):
        return self.submitter

    class Meta:
        permissions = (('view_job', 'Can view job'),)
