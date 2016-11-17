"""
Models for CoMSES.net
"""

from __future__ import absolute_import, unicode_literals

from django.db import models
from django.contrib.auth.models import User

from wagtail.wagtailcore.fields import StreamField
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.models import Page
from wagtailmenus.models import MenuPage
from wagtail.wagtailadmin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailsearch import index

from datetime import datetime


class HomePage(MenuPage):
    pass


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


class Author(models.Model):
    first_name = models.TextField(max_length=100, default='')
    middle_name = models.TextField(max_length=100, default='')
    last_name = models.TextField(max_length=100, default='')


class Event(index.Indexed, models.Model):
    title = models.TextField(max_length=1000)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()
    content = models.TextField(max_length=5000)
    # datetimerange_event = DateTimeRangeField()
    early_registration_deadline = models.DateTimeField(null=True)
    submission_deadline = models.DateTimeField(null=True)
    location = models.TextField(max_length=200)

    creator = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('content', partial_match=True),
        index.SearchField('creator'),
    ]


class Job(index.Indexed, models.Model):
    title = models.TextField(max_length=1000)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()
    content = models.TextField(max_length=5000)

    creator = models.ForeignKey(User)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('content', partial_match=True),
        index.SearchField('creator'),
    ]

    def __str__(self):
        return "{}. Created by {} on {}".format(self.title, self.creator.username, str(self.date_created))


class Profile(models.Model):
    """
    Additional academic information about a User
    """

    user = models.OneToOneField(User)

    degrees = models.TextField(max_length=500)
    summary = models.TextField(max_length=2000)
    picture = models.ImageField(null=True)

    academia_edu = models.URLField(null=True)
    blog = models.URLField(null=True)
    curriculum_vitae = models.URLField(null=True)
    institution = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    personal = models.URLField(null=True)
    research_gate = models.URLField(null=True)


class ModelKeywords(models.Model):
    model = models.ForeignKey('Model')
    keyword = models.ForeignKey('Keyword')


class Keyword(models.Model):
    name = models.TextField(max_length=100)

    def __str__(self):
        return self.name


class Model(index.Indexed, models.Model):
    title = models.TextField(max_length=1000)
    content = models.TextField(max_length=4000)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()

    keywords = models.ManyToManyField(Keyword, related_name='models', through=ModelKeywords)
    creator = models.ForeignKey(User)
    authors = models.ManyToManyField(Author)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('content', partial_match=True),
        index.SearchField('creator'),
    ]


class ModelVersion(models.Model):
    content = models.TextField(max_length=4000)
    documentation = models.TextField(max_length=12000)
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()

    model = models.ForeignKey(Model, related_name='modelversion_set')
