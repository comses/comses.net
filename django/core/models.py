import pathlib

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from enum import Enum
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TaggedItemBase
from timezone_field import TimeZoneField
from wagtail.contrib.settings.models import BaseSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailimages.models import Image
from wagtail.wagtailsearch import index
from wagtail.wagtailsnippets.models import register_snippet

from .fields import MarkdownField


class ComsesGroups(Enum):
    ADMIN = "Admins"
    EDITOR = "Editors"
    FULL_MEMBER = "Full Members"
    REVIEWER = "Reviewers"

    @staticmethod
    def initialize():
        return [
            Group.objects.get_or_create(name=g.value)[0] for g in ComsesGroups
        ]

    def get_group(self):
        _group = getattr(self, 'group', None)
        if _group is None:
            _group = self.group = Group.objects.get(name=self.value)
        return _group


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
                    ' e.g., `editors@openabm.org,info@openabm.org`'),
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
    target = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    source = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)

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

    """
    def with_codebases(self, user):
        return self.prefetch_related(
            models.Prefetch('user__codebases', Codebase.objects.accessible(user)))

    def public(self):
        return self.prefetch_related(models.Prefetch('user__codebases', Codebase.objects.public())) \
            .filter(user__is_active=True) \
            .exclude(user__username__in=('AnonymousUser', 'openabm'))
    """


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
    keywords = ClusterTaggableManager(through=MemberProfileTag, blank=True)

    personal_url = models.URLField(blank=True)
    picture = models.ForeignKey(Image, null=True, help_text=_('Profile picture'), on_delete=models.SET_NULL)
    professional_url = models.URLField(blank=True)
    research_interests = MarkdownField(max_length=512)

    objects = MemberProfileQuerySet.as_manager()

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
    def full_member(self):
        return self.user.groups.filter(name=ComsesGroups.FULL_MEMBER.value).exists()

    def get_absolute_url(self):
        return reverse('home:profile-detail', kwargs={'username': self.user.username})

    def __str__(self):
        return str(self.user)

    panels = [
        FieldPanel('bio', widget=forms.Textarea),
        FieldPanel('research_interests', widget=forms.Textarea),
        FieldPanel('personal_url'),
        FieldPanel('professional_url'),
        FieldPanel('orcid'),
        FieldPanel('institution'),
        ImageChooserPanel('picture'),
        InlinePanel('tagged_members'),
    ]

    search_fields = [
        index.SearchField('bio', partial_match=True, boost=10),
        index.SearchField('research_interests', partial_match=True),
        index.RelatedFields('institution', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('keywords', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('user', [
            index.SearchField('username'),
            index.SearchField('email'),
            index.SearchField('get_full_name'),
        ]),
    ]


class PlatformTag(TaggedItemBase):
    content_object = ParentalKey('core.Platform', related_name='tagged_platforms')


@register_snippet
class Platform(index.Indexed, ClusterableModel):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    description = MarkdownField(max_length=512, blank=True)
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
        FieldPanel('title'),
        FieldPanel('url'),
        FieldPanel('description'),
        FieldPanel('tags'),
    ]

    def get_all_tags(self):
        return ','.join(self.tags.all().values_list('name', flat=True))

    search_fields = [
        index.SearchField('name'),
        index.SearchField('description', partial_match=True),
        index.FilterField('active'),
        index.FilterField('open_source'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
    ]

    def __str__(self):
        return self.name


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
        start date and end date do not intersect with the interval
        :param start:
        :param end:
        :return:
        """
        return self.filter(
            # early registration deadline falls between the interval
            (models.Q(early_registration_deadline__gte=start) & models.Q(early_registration_deadline__lte=end)) |
            # or submission deadline falls between the interval
            (models.Q(submission_deadline__gte=start) & models.Q(submission_deadline__lte=end))
            # exclude any whose start date is after the interval end and whose end date is before the interval start
        ).exclude(models.Q(start_date__gte=end)).exclude(models.Q(end_date__lte=start))

    def upcoming(self):
        return self.public().filter(start_date__gte=timezone.now())

    def public(self):
        return self


class Event(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True)
    description = MarkdownField()
    early_registration_deadline = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300)
    tags = ClusterTaggableManager(through=EventTag, blank=True)
    external_url = models.URLField(blank=True)

    objects = EventQuerySet.as_manager()

    submitter = models.ForeignKey(User, on_delete=models.SET(get_sentinel_user))

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.FilterField('start_date'),
        index.FilterField('submission_deadline'),
        index.FilterField('early_registration_deadline'),
        index.SearchField('location'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('submitter', [
            index.SearchField('username'),
            index.SearchField('email'),
            index.SearchField('get_full_name'),
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
        ordering = ['-start_date']


class JobTag(TaggedItemBase):
    content_object = ParentalKey('core.Job', related_name='tagged_jobs')


class JobQuerySet(models.QuerySet):
    def public(self):
        return self


class Job(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300, help_text=_('Job posting title'))
    date_created = models.DateTimeField(default=timezone.now)
    application_deadline = models.DateField(blank=True, null=True, help_text=_('Optional deadline for applications'))
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True, help_text=_('Brief summary of job posting.'))
    description = MarkdownField()
    tags = ClusterTaggableManager(through=JobTag, blank=True)
    external_url = models.URLField(blank=True)

    submitter = models.ForeignKey(User, related_name='jobs', on_delete=models.SET(get_sentinel_user))

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
            index.SearchField('get_full_name'),
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
        ordering = ['-last_modified']
