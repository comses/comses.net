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

from wagtail.wagtailcore.fields import StreamField
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.models import Page, Orderable
from wagtailmenus.models import MenuPage
from wagtail.wagtailadmin.edit_handlers import FieldPanel, StreamFieldPanel, InlinePanel
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailsearch import index



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


class MemberProfile(index.Indexed, ClusterableModel):
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


class CarouselItem(models.Model):
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    caption = models.CharField(max_length=500, blank=True)

    class Meta:
        abstract = True

class FeaturedContentItem(Orderable, CarouselItem):
    page = ParentalKey('HomePage', related_name='featured_content_queue')


class HomePage(Page):
    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ])

    content_panels = [
        FieldPanel('title', classname='full title'),
        StreamFieldPanel('body'),
        InlinePanel('featured_content_queue', label=_('Featured Content')),
    ]


class BlogPage(MenuPage):
    date = models.DateField("Post Date")
    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ])

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        StreamFieldPanel('body'),
    ]


class EventTag(TaggedItemBase):
    content_object = ParentalKey('home.Event', related_name='tagged_events')


class Event(index.Indexed, ClusterableModel):
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
        index.SearchField('submitter'),
    ]


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
        index.SearchField('submitter'),
    ]

    def __str__(self):
        return "{0} posted by {1} on {2}".format(self.title, self.submitter.get_full_name(), str(self.date_created))
