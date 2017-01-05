from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from model_utils import Choices
from taggit.models import TaggedItemBase


from wagtail.wagtailsearch import index


class CodeKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='tagged_code_keywords')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='tagged_pl_code')


class License(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    url = models.URLField(blank=True)


class Platform(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True)


class Contributor(index.Indexed, models.Model):
    given_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    user = models.ForeignKey(User, null=True)


class Code(index.Indexed, ClusterableModel):
    title = models.CharField(max_length=370)
    description = models.TextField()
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    is_replication = models.BooleanField(default=False)

    # original Drupal data was stored inline like this
    # If this gets integrated with catalog these should be foreign keys and converted into M2M relationships

    # We should also allow a model to have multiple references
    reference = models.TextField()
    replication_reference = models.TextField()

    keywords = ClusterTaggableManager(through=CodeKeyword, blank=True)
    submitter = models.ForeignKey(User)
    contributors = models.ManyToManyField(Contributor, through='CodeContributor', through_fields=('code', 'contributor'))

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('submitter'),
    ]

    def __str__(self):
        return "{0} {1} ({2})".format(self.title, self.date_created, self.submitter)


class CodeContributor(models.Model):
    ROLES = Choices(
        ('Author', _('Author')),
        ('Architect', _('Architect')),
        ('Curator', _('Curator')),
        ('Designer', _('Designer')),
        ('Maintainer', _('Maintainer')),
        ('Submitter', _('Submitter')),
        ('Tester', _('Tester')),
    )
    # FIXME: should this be to CodeRelease instead?
    code = models.ForeignKey(Code, on_delete=models.CASCADE)
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, choices=ROLES, default=ROLES.Author)
    index = models.PositiveSmallIntegerField(help_text=_('Ordering field for code contributors'))


class CodeRelease(index.Indexed, models.Model):
    live = models.BooleanField(default=True)
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    documentation = models.TextField()
    embargo_end_date = models.DateField(null=True, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    os = models.CharField(max_length=100)
    license = models.ForeignKey(License, null=True)
    programming_language = ClusterTaggableManager(through=ProgrammingLanguage, blank=True)
    platform = models.ForeignKey(Platform, null=True)
    code = models.ForeignKey(Code, related_name='releases')
    release_number = models.CharField(max_length=32, help_text=_("Semver release number or 1,2,3"))
