from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TaggedItemBase

from timezone_field import TimeZoneField

from wagtail.wagtailadmin.edit_handlers import (FieldPanel, InlinePanel, PageChooserPanel, MultiFieldPanel)
from wagtail.wagtailcore.fields import StreamField
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsearch import index
from wagtailmenus.models import MenuPage

from wagtail_comses_net.permissions import PermissionMixin

"""
Wagtail-related models
"""


class Institution(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(null=True)
    acronym = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class MemberProfileTag(TaggedItemBase):
    content_object = ParentalKey('home.MemberProfile', related_name='tagged_members')


class MemberProfile(index.Indexed, ClusterableModel, PermissionMixin):
    """
    Contains additional comses.net information, possibly linked to a CoMSES Member / site account
    """
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL, related_name='member_profile')

    full_member = models.BooleanField(default=False, help_text=_('CoMSES Net Full Member'))

    # FIXME: add location field eventually, with postgis
    # location = LocationField(based_fields=['city'], zoom=7)

    timezone = TimeZoneField(blank=True)

    degrees = ArrayField(models.CharField(max_length=255), null=True)
    research_interests = models.TextField(blank=True)
    keywords = ClusterTaggableManager(through=MemberProfileTag, blank=True)
    summary = models.TextField(blank=True)

    picture = models.ImageField(null=True, help_text=_('Profile picture'))
    academia_edu_url = models.URLField(null=True)
    researchgate_url = models.URLField(null=True)
    linkedin_url = models.URLField(null=True)
    personal_homepage_url = models.URLField(null=True)
    institutional_homepage_url = models.URLField(null=True)
    blog_url = models.URLField(null=True)
    cv_url = models.URLField(null=True, max_length=500)
    institution = models.ForeignKey(Institution, null=True)
    affiliations = JSONField(default=list, help_text=_("JSON-LD list of affiliated institutions"))
    orcid = models.CharField(help_text=_("16 digits, - between every 4th digit, e.g., 0000-0002-1825-0097"),
                             max_length=19)

    @property
    def owner(self):
        return self.user


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
        # figure out how to link codebase / events / jobs into FeaturedContentItem
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
    caption = models.CharField(max_length=500)
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
    template = 'index.jinja'
    content_panels = [
        InlinePanel('featured_content_queue', label=_('Featured Content')),
    ]


class EventTag(TaggedItemBase):
    content_object = ParentalKey('home.Event', related_name='tagged_events')


class Event(index.Indexed, ClusterableModel, PermissionMixin):
    title = models.CharField(max_length=500)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    # datetimerange_event = DateTimeRangeField()
    early_registration_deadline = models.DateTimeField(null=True)
    submission_deadline = models.DateTimeField(null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    location = models.CharField(max_length=300)
    tags = ClusterTaggableManager(through=EventTag, blank=True)

    submitter = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.RelatedFields('submitter', [
            index.SearchField('username'),
            index.SearchField('get_full_name'),
        ]),
    ]

    @property
    def owner(self):
        return self.submitter


class JobTag(TaggedItemBase):
    content_object = ParentalKey('home.Job', related_name='tagged_jobs')


class Job(index.Indexed, ClusterableModel):
    # Help text is shown in OpenAPI
    title = models.CharField(max_length=500, help_text=_('Name of Job'))
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    tags = ClusterTaggableManager(through=JobTag, blank=True)

    submitter = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.RelatedFields('submitter', [
            index.SearchField('username'),
            index.SearchField('get_full_name'),
        ]),
    ]

    def __str__(self):
        return "{0} posted by {1} on {2}".format(self.title, self.submitter.get_full_name(), str(self.date_created))

    @property
    def owner(self):
        return self.submitter
