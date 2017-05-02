import logging
import pathlib
from enum import Enum

from django.contrib.auth.models import User, Group
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from timezone_field import TimeZoneField
from wagtail.contrib.settings.models import BaseSetting, register_setting
from wagtail.wagtailadmin.edit_handlers import (FieldPanel, InlinePanel, PageChooserPanel, MultiFieldPanel)
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsearch import index
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel
from wagtail.wagtailsnippets.models import register_snippet

logger = logging.getLogger(__name__)

"""
Wagtail Page models and related supporting Models and Settings

"""


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


@register_setting
class SocialMediaSettings(BaseSetting):
    facebook_url = models.URLField(help_text=_('Facebook URL'), blank=True)
    youtube_url = models.URLField(help_text=_('CoMSES Net YouTube Channel'), blank=True)
    twitter_account = models.CharField(max_length=128, help_text=_('CoMSES Net official Twitter account'), blank=True)
    mailing_list_url = models.URLField(help_text=_('Mailing List Signup'), blank=True)


class Institution(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    acronym = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class MemberProfileTag(TaggedItemBase):
    content_object = ParentalKey('home.MemberProfile', related_name='tagged_members')


class MemberProfile(index.Indexed, ClusterableModel):
    """
    Contains additional comses.net information, possibly linked to a CoMSES Member / site account
    """
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL, related_name='member_profile')

    # FIXME: add location field eventually, with postgis
    # location = LocationField(based_fields=['city'], zoom=7)

    timezone = TimeZoneField(blank=True)

    degrees = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    research_interests = models.TextField(blank=True)
    keywords = ClusterTaggableManager(through=MemberProfileTag, blank=True)
    summary = models.TextField(max_length=500, blank=True,
                               help_text=_('Brief bio'))
    picture = models.ImageField(null=True, help_text=_('Profile picture'))
    personal_url = models.URLField(blank=True)
    professional_url = models.URLField(blank=True)
    institution = models.ForeignKey(Institution, null=True)
    affiliations = JSONField(default=list, help_text=_("JSON-LD list of affiliated institutions"))
    orcid = models.CharField(help_text=_("16 digits, - between every 4th digit, e.g., 0000-0002-1825-0097"),
                             max_length=19)

    @property
    def full_member(self):
        return ComsesGroups.FULL_MEMBER.get_group() in self.groups

    def get_absolute_url(self):
        return reverse('home:profile-detail', kwargs={'username': self.user.username})

    def __str__(self):
        if self.user:
            return "username={} is_superuser={} is_active={}".format(self.user.username, self.user.is_superuser,
                                                                     self.user.is_active)
        else:
            return "id={}".format(self.id)

    search_fields = [
        index.SearchField('summary', partial_match=True, boost=10),
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


class LinkFields(models.Model):
    """
    Cribbed from github.com/wagtail/wagtaildemo
    """
    link_external = models.URLField("External link", blank=True)
    link_page = models.ForeignKey(
        Page,
        null=True,
        blank=True,
        related_name='+'
    )
    link_codebase = models.ForeignKey(
        'library.Codebase',
        null=True,
        blank=True,
        related_name='+'
    )

    @property
    def link(self):
        if self.link_page:
            return self.link_page.url
        elif self.link_codebase:
            return self.link_codebase.get_absolute_url()
        else:
            return self.link_external

    panels = [
        FieldPanel('link_external'),
        PageChooserPanel('link_page'),
        # figure out how to manually link codebase / events / jobs into FeaturedContentItem
        # CodebaseChooserPanel('link_codebase'),
    ]

    class Meta:
        abstract = True


class CarouselItem(LinkFields):
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    embed_url = models.URLField("Embed URL", blank=True)
    caption = models.CharField(max_length=255)
    summary = models.TextField(max_length=600, blank=True)
    title = models.CharField(max_length=255)

    panels = [
        ImageChooserPanel('image'),
        FieldPanel('embed_url'),
        FieldPanel('caption'),
        FieldPanel('title'),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    class Meta:
        abstract = True


class FeaturedContentItem(Orderable, CarouselItem):
    page = ParentalKey('home.LandingPage', related_name='featured_content_queue')


class LandingPage(Page):
    template = 'home/index.jinja'
    FEATURED_CONTENT_COUNT = 6
    MAX_CALLOUT_ENTRIES = 3

    mission_statement = models.CharField(max_length=512)

    def get_featured_content(self):
        return self.featured_content_queue.all()[:self.FEATURED_CONTENT_COUNT]

    def get_recent_forum_activity(self):
        return [
            {
                'title': 'This is a sequence of things that should come from Discourse',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            },
            {
                'title': 'This is something else that should come from Discourse',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            },
            {
                'title': 'And another',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            }
        ]

    def get_latest_jobs(self):
        return Job.objects.order_by('-date_created')[:self.MAX_CALLOUT_ENTRIES]

    def get_upcoming_events(self):
        return Event.objects.upcoming().order_by('start_date')[:self.MAX_CALLOUT_ENTRIES]

    def get_context(self, request):
        context = super(LandingPage, self).get_context(request)
        context['featured_content'] = self.get_featured_content()
        context['recent_forum_activity'] = self.get_recent_forum_activity()
        context['latest_jobs'] = self.get_latest_jobs()
        context['upcoming_events'] = self.get_upcoming_events()
        return context

    content_panels = Page.content_panels + [
        InlinePanel('featured_content_queue', label=_('Featured Content')),
    ]


class CategoryIndexItem(Orderable, models.Model):
    page = ParentalKey('home.CategoryIndexPage', related_name='callouts')
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    url = models.URLField("Linked page URL", blank=True)
    title = models.CharField(max_length=255)
    caption = models.CharField(max_length=600)


class CategoryIndexNavigationLink(Orderable, models.Model):
    page = ParentalKey('home.CategoryIndexPage', related_name='navigation_links')
    url = models.URLField("Linked URL")
    title = models.CharField(max_length=128)


class CategoryIndexPage(Page):
    # FIXME: CommunityIndexPage and ResourcesIndexPage could be merged into this wagtail Model
    template = 'home/category_index.jinja'
    heading = models.CharField(max_length=128, help_text=_("Short name to be placed in introduction header."))
    summary = models.CharField(max_length=1000, help_text=_('Summary blurb for this category index page.'))

    def get_navigation_links(self):
        """
        Returns a nested dict for use by the subnav Jinja2 tag.
        :return: 
        """
        return [
            {'url': nav.url, 'text': nav.title, 'active': self.slug in nav.url}
            for nav in self.navigation_links.all()
        ]

    content_panels = Page.content_panels + [
        InlinePanel('callouts', label=_('Captioned Image Callouts')),
        InlinePanel('navigation_links', label=_('Subnavigation Links')),
    ]

    search_fields = [
        index.SearchField('title'),
        index.SearchField('summary')
    ]


class CommunityIndexPage(Page):
    template = 'home/community/index.jinja'
    summary = models.CharField(max_length=500, help_text=_("Summary blurb for Community index"))


class ResourcesIndexPage(Page):
    template = 'home/resources/index.jinja'
    summary = models.CharField(max_length=500, help_text=_("Summary blurb for Resources index"))


class PlatformTag(TaggedItemBase):
    content_object = ParentalKey('home.Platform', related_name='tagged_platforms')


@register_snippet
class Platform(index.Indexed, ClusterableModel):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=512, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    url = models.URLField(blank=True)
    tags = TaggableManager(through=PlatformTag, blank=True)

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

    search_fields = [
        index.SearchField('name'),
        index.SearchField('description'),
        index.SearchField('active'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
    ]

    def __str__(self):
        return self.name


class PlatformRelease(models.Model):
    platform = models.ForeignKey(Platform)
    version = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    archive = models.FileField(upload_to=Platform._upload_path, null=True)


class PlatformSnippetPlacement(Orderable, models.Model):
    page = ParentalKey('home.PlatformsIndexPage', related_name='platform_placements')
    platform = models.ForeignKey(Platform)

    class Meta:
        verbose_name = 'platform placement'
        verbose_name_plural = 'platform placements'

    panels = [
        SnippetChooserPanel('platform'),
    ]

    def __str__(self):
        return "Snippet placement for {0}".format(self.platform.name)


class PlatformsIndexPage(Page):
    template = 'home/resources/platforms/index.jinja'

    content_panels = Page.content_panels + [
        InlinePanel('platform_placements', label='Platforms'),
    ]

    def get_platforms(self):
        # returns queryset of PlatformSnippetPlacements
        return self.platform_placements.exclude(platform__name='other').order_by('platform__name').all()

    def get_context(self, request):
        context = super().get_context(request)
        # FIXME: add pagination
        context['platforms'] = self.get_platforms()
        return context

class AboutPage(Page):
    template = 'home/about.jinja'


class NewsIndexPage(Page):
    def get_context(self, request):
        context = super(NewsIndexPage, self).get_context(request)
        context['news_entries'] = NewsPage.objects.child_of(self).live()
        return context


class NewsPage(Page):
    body = RichTextField()
    date = models.DateField("Post date")
    feed_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    search_fields = Page.search_fields + [
        index.SearchField('body'),
        index.FilterField('date')
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('body', classname="full"),
        InlinePanel('related_links', label="Related links"),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
        ImageChooserPanel('feed_image'),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['home.NewsIndexPage']
    subpage_types = []


class NewsPageRelatedLink(Orderable):
    page = ParentalKey(NewsPage, related_name='related_links')
    name = models.CharField(max_length=255)
    url = models.URLField()

    panels = [
        FieldPanel('name'),
        FieldPanel('url'),
    ]


class EventTag(TaggedItemBase):
    content_object = ParentalKey('home.Event', related_name='tagged_events')


class EventQuerySet(models.QuerySet):

    def upcoming(self):
        return self.filter(start_date__gte=timezone.now())


class Event(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    early_registration_deadline = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300)
    tags = ClusterTaggableManager(through=EventTag, blank=True)

    objects = EventQuerySet.as_manager()

    submitter = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('start_date'),
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

    def __str__(self):
        return "{} posted by {} on {}".format(repr(self.title), repr(self.submitter.username),
                                              str(self.date_created))

    class Meta:
        permissions = (('view_event', 'Can view events'),)


class JobTag(TaggedItemBase):
    content_object = ParentalKey('home.Job', related_name='tagged_jobs')


class Job(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=300, help_text=_('Job title'))
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    tags = ClusterTaggableManager(through=JobTag, blank=True)

    submitter = models.ForeignKey(User, related_name='jobs')

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('date_created'),
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

    def __str__(self):
        return "{0} posted by {1} on {2}".format(
            self.title,
            self.submitter.username,
            self.date_created.strftime('%c')
        )

    @property
    def owner(self):
        return self.submitter

    class Meta:
        permissions = (('view_job', 'Can view job'),)
