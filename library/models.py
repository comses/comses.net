from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from model_utils import Choices

from taggit.models import TaggedItemBase
from wagtail.wagtailsearch import index

import bagit
import logging
import pathlib
import semver
import shutil
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


class CodebaseKeyword(TaggedItemBase):
    content_object = ParentalKey('library.Codebase', related_name='tagged_codebase_keywords')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_languages')


class Platform(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    @staticmethod
    def _upload_path(instance, filename):
        return pathlib.Path('platforms', instance.name, filename)


class PlatformRelease(models.Model):
    platform = models.ForeignKey(Platform)
    version = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    archive = models.FileField(upload_to=Platform._upload_path, null=True)


class PlatformTag(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_platforms')


class ContributorAffiliation(TaggedItemBase):
    content_object = ParentalKey('library.Contributor')


class License(models.Model):
    name = models.CharField(max_length=200)
    text = models.TextField()
    url = models.URLField(blank=True)


class Contributor(index.Indexed, ClusterableModel):
    given_name = models.CharField(max_length=100, blank=True,
                                  help_text=_('Also doubles as organizational name'))
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    affiliations = ClusterTaggableManager(through=ContributorAffiliation)
    type = models.CharField(max_length=16,
                            choices=(('person', 'person'), ('organization', 'organization')),
                            default='person')
    email = models.EmailField(blank=True)
    user = models.ForeignKey(User, null=True)

    @property
    def name(self):
        return self.full_name

    @property
    def full_name(self):
        if self.type == 'person':
            return '{0} {1}'.format(self.given_name, self.family_name).strip()
        else:
            return self.given_name

    @property
    def formatted_affiliations(self):
        return ' '.join(self.affiliations.all())

    def __str__(self):
        return "{0} {1} {2}".format(self.full_name, self.email, self.formatted_affiliations)


class Codebase(index.Indexed, ClusterableModel):

    """
    Metadata applicable to a child set of CodebaseReleases

    """

    # shortname = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()

    live = models.BooleanField(default=False)
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    is_replication = models.BooleanField(default=False)
    peer_reviewed = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, blank=True, null=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    latest_version = models.ForeignKey('CodebaseRelease', null=True, related_name='latest_version')

    repository_url = models.URLField(blank=True,
                                     help_text=_('URL to actual source code repository, e.g., https://github.com/comses/cms'))
    # original Drupal data was stored inline like this
    # after catalog integration remove these / replace with M2M relationships
    # publication metadata
    # We should also allow a model to have multiple references
    references_text = models.TextField(blank=True)
    replication_references_text = models.TextField(blank=True)
    # M2M relationships for publications
    publications = models.ManyToManyField(
        'citation.Publication',
        through='CodebasePublication',
        related_name='codebases',
        help_text=_('Publications on this work'))
    references = models.ManyToManyField('citation.Publication',
                                        related_name='codebase_references',
                                        help_text=_('Related publications'))
    # consider storing related publications in JSON.
    relationships = JSONField(default=list)

    keywords = ClusterTaggableManager(through=CodebaseKeyword)
    submitter = models.ForeignKey(User)
    contributors = models.ManyToManyField(Contributor, through='CodebaseContributor')
    # should be stored in codebase base dir/images
    images = JSONField(default=list)

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('submitter'),
    ]

    @staticmethod
    def _release_upload_path(instance, filename):
        return instance.get_library_path('bagit', 'sip', filename)

    @property
    def base_library_dir(self):
        # FIXME: slice up UUID eventually if needed
        return pathlib.Path(settings.LIBRARY_ROOT, self.uuid)

    @property
    def base_git_dir(self):
        return pathlib.Path(settings.REPOSITORY_ROOT, self.uuid)

    def make_release(self, archive=None, submitter=None, major=False, minor=False, patch=False, **kwargs):
        if submitter is None:
            submitter = self.submitter
        version_number = '1.0.0'
        if self.latest_version is not None:
            version_number = self.latest_version.version_number
            if major:
                version_number = semver.bump_major(version_number)
            elif minor:
                version_number = semver.bump_minor(version_number)
            elif patch:
                version_number = semver.bump_patch(version_number)
            else:
                version_number = semver.bump_minor(version_number)
                logger.debug("No explicit guidance on how to increment version number, making new minor release: %s",
                             version_number)
        release = self.releases.create(
            submitter=submitter,
            submitted_package=archive,
            version_number=version_number,
            **kwargs
        )
        self.latest_version = release
        self.save()
        return release

    def __str__(self):
        return "{0} {1} ({2})".format(self.title, self.date_created, self.submitter)


class CodebasePublication(models.Model):
    codebase = models.ForeignKey(Codebase, on_delete=models.CASCADE)
    publication = models.ForeignKey('citation.Publication', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    index = models.PositiveIntegerField(default=1)


class CodebaseContributor(models.Model):

    # FIXME: decide if we are tracking contributions to each CodebaseRelease or the Codebase as a whole
    codebase = models.ForeignKey(Codebase, on_delete=models.CASCADE)
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE)
    include_in_citation = models.BooleanField(default=True)
    is_maintainer = models.BooleanField(default=False)
    is_rights_holder = models.BooleanField(default=False)
    role = models.CharField(max_length=100, choices=ROLES, default=ROLES.author,
                            help_text=_('''
                            Roles from https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode
                            '''))
    index = models.PositiveSmallIntegerField(help_text=_('Ordering field for codebase contributors'))


class CodebaseRelease(index.Indexed, ClusterableModel):
    """
    A snapshot of a codebase at a particular moment in time, versioned and addressable in a git repo behind-the-scenes
    and a bagit repository.

    For now, simple FS organization in lieu of HashFS or other content addressable filesystem.

    * release tarballs or zipfiles located at /library/<codebase_identifier>/releases/<release_identifier>/<version_number>.(tar.gz|zip)
    * release bagits at /library/<codebase_identifier>/releases/<release_identifier>/bagit/
    *  git repository in /repository/<codebase_identifier>/
    """

    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    peer_reviewed = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, blank=True, null=True)

    dependencies = JSONField(
        default=list,
        help_text=_('JSON list of software dependencies (identifier, name, version, packageSystem, OS, URL)')
    )

    license = models.ForeignKey(License, null=True)
    # FIXME: replace with README.md
    description = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    embargo_end_date = models.DateField(null=True, blank=True)
    version_number = models.CharField(max_length=32,
                                      help_text=_('semver string, e.g., 1.0.5, see semver.org'))

    os = models.CharField(max_length=32, choices=OPERATING_SYSTEMS, blank=True)
    '''
    FIXME: platforms / programming languages could be covered via dependencies, need to decide which
    is the central source of truth. Or we could augment dependencies JSON field with structured metadata and
    leave it as the junk drawer.
    '''
    platforms = ClusterTaggableManager(through=PlatformTag, related_name='platform_codebase_releases')
    programming_languages = ClusterTaggableManager(through=ProgrammingLanguage,
                                                   related_name='pl_codebase_releases')
    codebase = models.ForeignKey(Codebase, related_name='releases')
    submitted_package = models.FileField(upload_to=Codebase._release_upload_path, null=True)
    submitter = models.ForeignKey(User)

    def get_library_path(self, *args):
        return pathlib.Path(self.codebase.base_library_dir, 'releases', self.pk, *args)

    @property
    def bagit_path(self):
        return self.get_library_path('bagit')

    @property
    def git_path(self):
        return self.codebase.base_git_dir

    @property
    def submitted_package_path(self):
        return self.get_library_path('bagit', 'sip')

    def make_bagit(self):
        if self.submitted_package is None:
            logger.debug("%s has no submission file to archive", self.identifier)
            return
        else:
            try:
                bag = bagit.Bag(self.bagit_path)
                logger.debug("Valid bag already found for %s - ignoring request to archive", self.identifier)
                return bag.is_valid()
            except bagit.BagError:
                bag = bagit.make_bag(self.bagit_path, {
                    'Contact-Name': self.submitter.get_full_name(),
                    'Contact-Email': self.submitter.email,
                })
                return bag

    class Meta:
        unique_together = ('codebase', 'version_number')
