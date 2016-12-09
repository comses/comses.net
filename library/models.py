from django.contrib.auth.models import User
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.wagtailsearch import index

class CodeKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='keyword_set')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='programming_language')


class Author(models.Model):
    given_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL)


class Code(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=370)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_replicated = models.BooleanField()

    # The original data was stored inline like this
    # If this gets integrated with catalog these should be foreign keys

    # We should also allow one model to have multiple references
    reference = models.TextField()
    replication_reference = models.TextField()

    keywords = ClusterTaggableManager(through=CodeKeyword, blank=True)
    creator = models.ForeignKey(User)
    authors = models.ManyToManyField(Author)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('creator'),
    ]


class License(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    url = models.URLField(blank=True)


class Platform(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True)


class CodeRelease(models.Model):
    live = models.BooleanField(default=True)
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    documentation = models.TextField()
    embargo_end_date = models.DateField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    os = models.CharField(max_length=100)
    license = models.ForeignKey(License, null=True)
    programming_language = ClusterTaggableManager(through=ProgrammingLanguage, blank=True)
    platform = models.ForeignKey(Platform)
    code = models.ForeignKey(Code, related_name='version_set')
