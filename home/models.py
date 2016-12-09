"""
Models for CoMSES.net
"""

from __future__ import absolute_import, unicode_literals

from django.db import models
from django.contrib.auth.models import User
from modelcluster.fields import ParentalKey

from wagtail.wagtailcore.fields import StreamField
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.models import Page, Orderable
from wagtailmenus.models import MenuPage
from wagtail.wagtailadmin.edit_handlers import FieldPanel, StreamFieldPanel, InlinePanel
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailsearch import index

from django.utils.translation import ugettext_lazy as _

from datetime import datetime


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


class Event(index.Indexed, models.Model):
    title = models.CharField(max_length=500)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()
    description = models.TextField()
    # datetimerange_event = DateTimeRangeField()
    early_registration_deadline = models.DateTimeField(null=True)
    submission_deadline = models.DateTimeField(null=True)
    location = models.CharField(max_length=200)

    creator = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('creator'),
    ]


class Job(index.Indexed, models.Model):
    title = models.CharField(max_length=500)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()
    description = models.TextField()

    creator = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('creator'),
    ]

    def __str__(self):
        return "{}. Created by {} on {}".format(self.title, self.creator.username, str(self.date_created))


class Profile(models.Model):
    """
    Additional academic information about a User
    """

    user = models.OneToOneField(User, help_text=_('User associated with profile'))

    degrees = models.CharField(max_length=500)
    summary = models.TextField()
    picture = models.ImageField(null=True, help_text=_('Picture of user'))

    academia_edu_url = models.URLField(null=True)
    linkedin_url = models.URLField(null=True)
    personal_homepage_url = models.URLField(null=True)
    institutional_homepage_url = models.URLField(null=True)
    research_gate_url = models.URLField(null=True)
    blog = models.URLField(null=True)
    curriculum_vitae = models.URLField(null=True)
    institution = models.URLField(null=True)
    orcid = models.CharField(help_text=_("16 digit number with - at every 4, e.g., 0000-0002-1825-0097"),
                             max_length=19)
