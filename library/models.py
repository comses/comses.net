from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from model_utils import Choices
from taggit.models import TaggedItemBase

from wagtail.wagtailsearch import index

class CodeKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='keyword_set')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='programming_language')


class ResearchKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Person', related_name='keywords')


class License(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    url = models.URLField(blank=True)


class Platform(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True)


class Institution(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(null=True)
    acronym = models.CharField(max_length=50)


class Person(models.Model):
    """
    Contains additional comses.net information, possibly linked to a CoMSES Member / site account
    """
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL)

    full_member = models.BooleanField(default=False, help_text=_('CoMSES Net Full Member'))


    # FIXME: add location field eventually, with postgis
    # location = LocationField(based_fields=['city'], zoom=7)

    given_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    degrees = ArrayField(models.CharField(max_length=255))
    institutions = JSONField(default=dict)
    research_interests = models.TextField()
    research_keywords = ClusterTaggableManager(through=ResearchKeyword, blank=True)
    summary = models.TextField()

    picture = models.ImageField(null=True, help_text=_('Picture of user'))
    academia_edu_url = models.URLField(null=True)
    research_gate_url = models.URLField(null=True)
    linkedin_url = models.URLField(null=True)
    personal_homepage_url = models.URLField(null=True)
    institutional_homepage_url = models.URLField(null=True)

    blog_url = models.URLField(null=True)
    cv_url = models.URLField(null=True)
    institution = models.ForeignKey(Institution)
    orcid = models.CharField(help_text=_("16 digit number with - at every 4, e.g., 0000-0002-1825-0097"),
                             max_length=19)



class Code(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=370)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_replication = models.BooleanField(default=False)

    # original Drupal data was stored inline like this
    # If this gets integrated with catalog these should be foreign keys and converted into M2M relationships

    # We should also allow a model to have multiple references
    reference = models.TextField()
    replication_reference = models.TextField()

    keywords = ClusterTaggableManager(through=CodeKeyword, blank=True)
    submitter = models.ForeignKey(User)
    authors = models.ManyToManyField(Person, through='Contributor', through_fields=('code', 'person'))

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('submitter'),
    ]

    def __str__(self):
        return "{0} {1} ({2})".format(self.title, self.date_created, self.submitter)


class Contributor(models.Model):
    ROLES = Choices(
        ('Author', _('Author')),
        ('Architect', _('Architect')),
        ('Curator', _('Curator')),
        ('Designer', _('Designer')),
        ('Maintainer', _('Maintainer')),
        ('Submitter', _('Submitter')),
        ('Tester', _('Tester')),
    )
    code = models.ForeignKey(Code, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, choices=ROLES, default=ROLES.Author)
    index = models.PositiveSmallIntegerField(help_text=_('Ordering field for code contributors'))


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
    code = models.ForeignKey(Code, related_name='releases')
