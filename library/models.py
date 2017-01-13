from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from model_utils import Choices

from taggit.models import TaggedItemBase
from wagtail.wagtailsearch import index

import logging
import uuid

logger = logging.getLogger(__name__)

# Cherry picked from
# https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode
ROLES = Choices(
    ('author', _('Author')),
    ('publisher', _('Publisher')),
    ('custodian', _('Custodian')),
    ('resourceProvider', _('Resource Provider')),
    ('maintainer', _('Maintainer')),
    ('pointOfContact', _('Point of contact')),
    ('editor', _('Editor')),
    ('contributor', _('Contributor')),
    ('collaborator', _('Collaborator')),
    ('funder', _('Funder')),
    ('copyrightHolder', _("Copyright holder")),
)

OPERATING_SYSTEMS = Choices(
    ('other', _('Other')),
    ('linux', _('Unix/Linux')),
    ('macos', _('Mac OS')),
    ('windows', _('Windows')),
    ('platform_independent', _('Platform Independent')),
)


class CodeKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Code', related_name='tagged_code_keywords')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.CodeRelease', related_name='tagged_release_languages')
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)


class Platform(TaggedItemBase):
    content_object = ParentalKey('library.CodeRelease', related_name='tagged_release_platforms')
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)


class ContributorAffiliation(TaggedItemBase):
    content_object = ParentalKey('library.Contributor')


class License(models.Model):
    name = models.CharField(max_length=100)
    text = models.TextField()
    url = models.URLField(blank=True)


class Contributor(index.Indexed, ClusterableModel):
    given_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    affiliation = ClusterTaggableManager(through=ContributorAffiliation, blank=True)
    type = models.CharField(max_length=16,
                            choices=(('person', 'person'), ('organization', 'organization')),
                            default='person')
    email = models.EmailField(blank=True)
    user = models.ForeignKey(User, null=True)

    @property
    def full_name(self):
        if self.type == 'person':
            return '{0} {1}'.format(self.given_name, self.family_name).strip()
        else:
            return self.given_name

    def __str__(self):
        return "{0} ({1})".format(self.full_name, self.affiliation)


class Code(index.Indexed, ClusterableModel):
    # shortname = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()

    live = models.BooleanField(default=False)
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    is_replication = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, blank=True, null=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    repository_url = models.URLField(blank=True)

    # original Drupal data was stored inline like this
    # after catalog integration these should be foreign keys and converted into M2M relationships

    # publication metadata
    # We should also allow a model to have multiple references
    references_text = models.TextField()
    replication_references_text = models.TextField()
    # M2M relationships for publications
    publications = models.ManyToManyField(
        'citation.Publication',
        through='CodePublication',
        related_name='code_publications',
        help_text=_('Publications on this work'))
    references = models.ManyToManyField('citation.Publication',
                                        related_name='code_references',
                                        help_text=_('Related publications'))
    relationships = JSONField(default=list)

    keywords = ClusterTaggableManager(through=CodeKeyword, blank=True)
    submitter = models.ForeignKey(User)
    contributors = models.ManyToManyField(Contributor, through='CodeContributor')
    # should be stored in code project directory
    images = JSONField(default=list)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('submitter'),
    ]

    def __str__(self):
        return "{0} {1} ({2})".format(self.title, self.date_created, self.submitter)


class CodePublication(models.Model):
    code = models.ForeignKey(Code, on_delete=models.CASCADE)
    publication = models.ForeignKey('citation.Publication', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    index = models.PositiveIntegerField(default=1)


class CodeContributor(models.Model):

    # FIXME: should this be to CodeRelease instead?
    code = models.ForeignKey(Code, on_delete=models.CASCADE)
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE)
    include_in_citation = models.BooleanField(default=True)
    is_maintainer = models.BooleanField(default=False)
    is_rights_holder = models.BooleanField(default=False)
    role = models.CharField(max_length=100, choices=ROLES, default=ROLES.author,
                            help_text=_('''
                            Roles from https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode
                            '''))
    index = models.PositiveSmallIntegerField(help_text=_('Ordering field for code contributors'))


class CodeRelease(index.Indexed, ClusterableModel):

    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    peer_reviewed = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, blank=True, null=True)

    dependencies = JSONField(
        default=list,
        help_text=_('List of JSON dependencies (identifier, name, version, packageSystem, OS, URL)')
    )

    description = models.TextField()
    documentation = models.TextField()
    embargo_end_date = models.DateField(null=True, blank=True)

    release_number = models.CharField(max_length=32,
                                      help_text=_("Simple or semver version number, e.g., v1/v2/v3 or v1.0.0, v1.0.1"))

    os = models.CharField(max_length=32, choices=OPERATING_SYSTEMS, blank=True)
    platforms = ClusterTaggableManager(through=Platform, blank=True, related_name='platform_code_releases')
    programming_languages = ClusterTaggableManager(through=ProgrammingLanguage, blank=True,
                                                   related_name='pl_code_releases')
    code = models.ForeignKey(Code, related_name='releases')
