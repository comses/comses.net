import logging
import os
import pathlib
import shutil
import uuid
from enum import Enum
from zipfile import ZipFile

import semver
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils._os import safe_join
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from rest_framework.exceptions import ValidationError
from taggit.models import TaggedItemBase
from wagtail.wagtailimages.models import Image
from wagtail.wagtailsearch import index

from core import fs
from core.backends import get_viewable_objects_for_user
from core.fields import MarkdownField

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


class CodebaseTag(TaggedItemBase):
    content_object = ParentalKey('library.Codebase', related_name='tagged_codebases')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_languages')


class CodebaseReleasePlatformTag(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_platforms')


class ContributorAffiliation(TaggedItemBase):
    content_object = ParentalKey('library.Contributor')


class License(models.Model):
    name = models.CharField(max_length=200, help_text=_('SPDX license code from https://spdx.org/licenses/'))
    url = models.URLField(blank=True)


class Contributor(index.Indexed, ClusterableModel):
    given_name = models.CharField(max_length=100, blank=True,
                                  help_text=_('Also doubles as organizational name'))
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    affiliations = ClusterTaggableManager(through=ContributorAffiliation)
    type = models.CharField(max_length=16,
                            choices=(('person', 'person'), ('organization', 'organization')),
                            default='person',
                            help_text=_('organizations only use given_name'))
    email = models.EmailField(blank=True)
    user = models.ForeignKey(User, null=True)

    @property
    def name(self):
        return self.get_full_name()

    def get_full_name(self, family_name_first=False):
        if self.type == 'person':
            # Bah
            if family_name_first:
                return '{0}, {1} {2}'.format(self.family_name, self.given_name, self.middle_name).strip()
            elif self.middle_name:
                return '{0} {1} {2}'.format(self.given_name, self.middle_name, self.family_name)
            else:
                return '{0} {1}'.format(self.given_name, self.family_name)
        else:
            return self.given_name

    @property
    def formatted_affiliations(self):
        return ' '.join(self.affiliations.all())

    def __str__(self):
        if self.email:
            return '{0} {1}'.format(self.get_full_name(), self.email)
        return self.get_full_name()


class SemanticVersionBump(Enum):
    MAJOR = semver.bump_major
    MINOR = semver.bump_minor
    PATCH = semver.bump_patch


class CodebaseReleaseDownload(models.Model):
    date_created = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, null=True)
    ip_address = models.GenericIPAddressField()
    referrer = models.URLField(max_length=500)
    release = models.ForeignKey('library.CodebaseRelease', related_name='downloads')

    def __str__(self):
        return "{0}: downloaded {1}".format(self.ip_address, self.release)


class CodebaseQuerySet(models.QuerySet):
    def accessible(self, user):
        return get_viewable_objects_for_user(user=user, queryset=self)

    def contributed_by(self, user):
        contributed_codebases = ReleaseContributor.objects.filter(contributor__user=user).values_list('release__codebase',
                                                                                                      flat=True)
        # FIXME: consider replacing submitter with ReleaseContributor, see
        # https://github.com/comses/core.comses.net/issues/129 for more details
        return self.accessible(user=user).filter(models.Q(pk__in=contributed_codebases) | models.Q(submitter=user))

    def public(self, **kwargs):
        return self.filter(live=True, **kwargs)

    def peer_reviewed(self, **kwargs):
        return self.public(**kwargs).filter(peer_reviewed=True)


class Codebase(index.Indexed, ClusterableModel):
    """
    Metadata applicable across a set of CodebaseReleases
    """
    # shortname = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=300)
    description = MarkdownField()
    summary = models.CharField(max_length=500, blank=True)

    featured = models.BooleanField(default=False)

    live = models.BooleanField(default=False)
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    last_published_on = models.DateTimeField(null=True, blank=True)

    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)
    is_replication = models.BooleanField(default=False, help_text=_("Is this model a replication of another model?"))
    # FIXME: should this be a rollup of peer reviewed CodebaseReleases?
    peer_reviewed = models.BooleanField(default=False)

    # FIXME: right now leaning towards identifier as the agnostic way to ID any given Codebase. It is currently set to the
    # old Drupal NID but that means we need to come up with something on model upload
    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, null=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    latest_version = models.ForeignKey('CodebaseRelease', null=True, related_name='latest_version')

    repository_url = models.URLField(blank=True,
                                     help_text=_('URL to code repository, e.g., https://github.com/comses/wolf-sheep'))
    # FIXME: original Drupal data was stored inline like this
    # after catalog integration remove these / replace with M2M relationships
    # publication metadata
    # We should also allow a model to have multiple references
    references_text = models.TextField(blank=True)
    associated_publication_text = models.TextField(blank=True)
    tags = ClusterTaggableManager(through=CodebaseTag)
    # evaluate this JSONField as an add-anything way to record relationships between this Codebase and other entities
    # with URLs / resolvable identifiers
    relationships = JSONField(default=list)

    # JSONField list of image metadata records with paths referring to self.media_dir()
    media = JSONField(default=list,
                      help_text=_("JSON metadata dict of media associated with this Codebase"))

    featured_images = models.ManyToManyField(Image)

    submitter = models.ForeignKey(User, related_name='codebases')

    objects = CodebaseQuerySet.as_manager()

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('featured'),
        index.SearchField('first_published_at'),
        index.SearchField('last_published_on'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
    ]

    @property
    def deletable(self):
        return not self.live

    @staticmethod
    def _release_upload_path(instance, filename):
        return str(pathlib.Path(instance.codebase.upload_path, filename))

    @staticmethod
    def assign_latest_release():
        for codebase in Codebase.objects.all():
            codebase.latest_version = codebase.releases.order_by('-version_number').first()
            codebase.save()

    def as_featured_content_dict(self):
        return dict(
            title=self.title,
            summary=self.summarized_description,
            image=self.get_featured_image(),
            link_codebase=self,
        )

    def get_featured_image(self):
        if self.featured_images.exists():
            return self.featured_images.first()
        return None

    def subpath(self, *args):
        return pathlib.Path(self.base_library_dir, *args)

    @property
    def upload_path(self):
        return self.media_dir('uploads')

    def media_dir(self, *args):
        return pathlib.Path(settings.MEDIA_ROOT, str(self.uuid), *args)

    @property
    def summarized_description(self):
        if self.summary:
            return self.summary
        lines = self.description.raw.splitlines()
        max_lines = 6
        if len(lines) > max_lines:
            # FIXME: add a "more.." link, is this type of summarization more appropriate in JS?
            return "{0} \n...".format(
                "\n".join(lines[:max_lines])
            )
        return self.description.raw

    @property
    def base_library_dir(self):
        # FIXME: slice up UUID eventually if needed
        return pathlib.Path(settings.LIBRARY_ROOT, str(self.uuid))

    @property
    def base_git_dir(self):
        return pathlib.Path(settings.REPOSITORY_ROOT, str(self.uuid))

    @property
    def all_contributors(self):
        return ReleaseContributor.objects.select_related('release', 'contributor').filter(
            release__codebase__id=self.pk).distinct('contributor')

    @property
    def contributor_list(self):
        contributor_list = [c.contributor.get_full_name(family_name_first=True) for c in
                            self.all_contributors]
        return contributor_list

    def download_count(self):
        return CodebaseReleaseDownload.objects.filter(release__codebase__id=self.pk).aggregate(
            count=models.Count('id'))['count']

    @classmethod
    def get_list_url(cls):
        return reverse('library:codebase-list')

    def get_absolute_url(self):
        return reverse('library:codebase-detail', kwargs={'identifier': self.identifier})

    def media_url(self, name):
        return '{0}/media/{1}'.format(self.get_absolute_url(), name)

    def next_version_number(self, version_number=None, version_bump=SemanticVersionBump.MINOR):
        if version_number is None:
            # start off at v1.0.0
            version_number = '1.0.0'
            # check for the latest version and reinitialize if it exists
            if self.latest_version is not None:
                version_number = version_bump(self.latest_version.version_number)
        return version_number

    def import_release(self, submitter=None, submitter_id=None, version_number=None, submitted_package=None, **kwargs):
        if submitter_id is None:
            if submitter is None:
                submitter = User.objects.first()
                logger.warning("No submitter or submitter_id specified when creating release, using first user %s",
                               submitter)
            submitter_id = submitter.pk
        if version_number is None:
            version_number = self.next_version_number()

        identifier = kwargs.pop('identifier', None)
        release = CodebaseRelease.objects.create(
            submitter_id=submitter_id,
            version_number=version_number,
            identifier=identifier,
            codebase=self,
            **kwargs)
        if submitted_package:
            release.submitted_package.save(submitted_package.name, submitted_package, save=False)
        self.latest_version = release
        self.save()
        return release

    def __str__(self):
        return "{0} {1} identifier={2} live={3}".format(self.title, self.date_created, repr(self.identifier),
                                                        repr(self.live))

    class Meta:
        permissions = (('view_codebase', 'Can view codebase'),)


class CodebasePublication(models.Model):
    release = models.ForeignKey('library.CodebaseRelease', on_delete=models.CASCADE)
    publication = models.ForeignKey('citation.Publication', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    index = models.PositiveIntegerField(default=1)


class CodebaseRelease(index.Indexed, ClusterableModel):
    """
    A snapshot of a codebase at a particular moment in time, versioned and addressable in a git repo behind-the-scenes
    and a bagit repository.

    Currently using simple FS organization in lieu of HashFS or other content addressable filesystem.

    * release tarballs or zipfiles located at /library/<codebase_identifier>/releases/<version_number>/<id>.(tar.gz|zip)
    * release bagits at /library/<codebase_identifier>/releases/<release_identifier>/sip
    * git repository in /repository/<codebase_identifier>/
    """

    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    live = models.BooleanField(default=False, help_text=_("Signifies that this release is public."))
    # there should only be one draft CodebaseRelease ever
    draft = models.BooleanField(default=False, help_text=_("Signifies that this release is currently being edited."))
    has_unpublished_changes = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    last_published_on = models.DateTimeField(null=True, blank=True)

    peer_reviewed = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True, null=True)
    doi = models.CharField(max_length=128, unique=True, null=True)
    license = models.ForeignKey(License, null=True)
    # FIXME: replace with or append/prepend README.md
    description = MarkdownField(blank=True, help_text=_('Markdown formattable text, e.g., run conditions'))
    summary = models.CharField(max_length=500, blank=True)
    documentation = models.FileField(null=True, help_text=_('Fulltext documentation file (PDF/PDFA)'))
    embargo_end_date = models.DateField(null=True, blank=True)
    version_number = models.CharField(max_length=32,
                                      help_text=_('semver string, e.g., 1.0.5, see semver.org'))

    os = models.CharField(max_length=32, choices=OPERATING_SYSTEMS, blank=True)
    dependencies = JSONField(
        default=list,
        help_text=_('JSON list of software dependencies (identifier, name, version, packageSystem, OS, URL)')
    )
    '''
    platform and programming language tags are also dependencies that can reference additional metadata in the
    dependencies JSONField
    '''
    platform_tags = ClusterTaggableManager(through=CodebaseReleasePlatformTag,
                                           related_name='platform_codebase_releases')
    platforms = models.ManyToManyField('core.Platform')
    programming_languages = ClusterTaggableManager(through=ProgrammingLanguage,
                                                   related_name='pl_codebase_releases')
    codebase = models.ForeignKey(Codebase, related_name='releases')
    submitter = models.ForeignKey(User)
    contributors = models.ManyToManyField(Contributor, through='ReleaseContributor')
    submitted_package = models.FileField(upload_to=Codebase._release_upload_path, null=True)
    # M2M relationships for publications
    publications = models.ManyToManyField(
        'citation.Publication',
        through=CodebasePublication,

        related_name='releases',
        help_text=_('Publications on this work'))
    references = models.ManyToManyField('citation.Publication',
                                        related_name='codebase_references',
                                        help_text=_('Related publications'))

    def get_library_path(self, *args):
        """
        Currently <codebase.path>/releases/<version_number>/arg0/arg1/arg2/.../argn
        :param args: args are joined as subpaths of
        :return: full pathlib.Path to this codebase release with args subpaths
        """
        return self.codebase.subpath('releases', 'v{0}'.format(self.version_number), *map(str, args))

    def get_absolute_url(self):
        return reverse('library:codebaserelease-detail',
                       kwargs={'identifier': self.codebase.identifier, 'version_number': self.version_number})

    # FIXME: lift magic constants
    @property
    def handle_url(self):
        if '2286.0/oabm' in self.doi:
            return 'http://hdl.handle.net/{0}'.format(self.doi)
        return None

    @property
    def doi_url(self):
        return 'http://dx.doi.org/{0}'.format(self.doi)

    @property
    def permanent_url(self):
        if self.doi:
            if '2286.0/oabm' in self.doi:
                return self.handle_url
            else:
                return self.doi_url
        return 'https://www.comses.net{0}'.format(self.get_absolute_url())

    @property
    def citation_text(self):
        authors = ', '.join(self.contributor_list)
        return '{authors} ({publish_date}). "{title}" (Version {version}). _{cml}_. Retrieved from: {purl}'.format(
            authors=authors,
            publish_date=self.last_published_on.strftime('%Y, %B %d'),
            title=self.codebase.title,
            version=self.version_number,
            cml='CoMSES Computational Model Library',
            purl=self.permanent_url
        ) if self.last_published_on else 'You must publish this model in order to cite it'

    def download_count(self):
        return self.downloads.count()

    @property
    def contributor_list(self):
        return [c.contributor.get_full_name(family_name_first=True) for c in
                self.codebase_contributors.order_by('index')]

    @property
    def bagit_path(self):
        return self.get_library_path('bagit')

    @property
    def git_path(self):
        return self.codebase.base_git_dir

    @property
    def workdir_path(self):
        ''' a working directory scratch space path'''
        return self.get_library_path('workdir')

    def submitted_package_path(self, *args):
        return self.get_library_path('sip', *args)

    @property
    def archival_information_package_path(self):
        return self.bagit_path

    @property
    def archive_path(self):
        return self.get_library_path('archive.zip')

    def save_file(self, file_obj):
        """Extract the archive, inspect it's contents and if it's valid store with other releases"""
        pass

    @property
    def index_ordered_release_contributors(self):
        return self.codebase_contributors.order_by('index')

    def _add_file(self, fileobj, destination_folder: str):
        path = safe_join(str(self.workdir_path), destination_folder, fileobj.name)
        logger.debug('add file path %s', path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as source_file:
            shutil.copyfileobj(fileobj, source_file)

    def _add_archive_file(self, fileobj, destination_folder: str):
        base_path = str(self.workdir_path)
        archive_path = safe_join(base_path, fileobj.name)
        path = safe_join(base_path, destination_folder)

        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        os.makedirs(path, exist_ok=True)

        with open(archive_path, 'wb') as archive:
            shutil.copyfileobj(fileobj, archive)
        shutil.unpack_archive(archive_path, path)

    UPLOAD_TYPE_TO_FOLDERNAME = {'data': 'data', 'documentation': 'doc', 'sources': 'code', 'images': 'images'}

    def get_absolute_upload_retrieve_url(self, upload_type: str, relpath: str):
        return reverse('library:codebaserelease-download',
                       kwargs={'identifier': self.codebase.identifier, 'version_number': self.version_number,
                               'upload_type': upload_type, 'path': relpath})

    def add_upload(self, upload_type: str, fileobj):
        foldername = self.UPLOAD_TYPE_TO_FOLDERNAME[upload_type]
        name = os.path.basename(fileobj.name)
        if fs.is_archive(name):
            self._add_archive_file(fileobj, foldername)
        else:
            self._add_file(fileobj, foldername)

    def list_uploads(self, upload_type: str):
        foldername = self.UPLOAD_TYPE_TO_FOLDERNAME[upload_type]
        rootdir = safe_join(str(self.workdir_path), foldername)
        paths = []
        for dirpath, dirnames, filenames in os.walk(rootdir):
            for filename in filenames:
                relpath = os.path.relpath(os.path.join(dirpath, filename), rootdir)
                paths.append(
                    dict(path=relpath, url=self.get_absolute_upload_retrieve_url(upload_type, relpath)))
        return paths

    def delete_upload(self, upload_type: str, relpath: str):
        foldername = self.UPLOAD_TYPE_TO_FOLDERNAME[upload_type]
        path = safe_join(str(self.workdir_path), foldername, relpath)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)

    def retrieve_upload(self, upload_type: str, relpath: str):
        foldername = self.UPLOAD_TYPE_TO_FOLDERNAME[upload_type]
        path = safe_join(str(self.workdir_path), foldername, relpath)
        if os.path.isfile(path):
            return open(path, 'rb')
        else:
            raise FileNotFoundError('File "{}" does not exist'.format(relpath))

    def retrieve_archive(self):
        if not self.archive_path.exists():
            sip_path = self.submitted_package_path()
            if sip_path.exists():
                with ZipFile(str(self.archive_path), 'w') as archive:
                    for root_path, dirs, file_paths in os.walk(str(sip_path)):
                        for file_path in file_paths:
                            path = pathlib.Path(root_path, file_path)
                            archive.write(str(path), arcname=str(path.relative_to(sip_path)))
            else:
                raise FileNotFoundError(
                    'submission package for release {} {} not found'.format(self.codebase.title, self.version_number))
        return open(str(self.archive_path), 'rb')

    @property
    def bagit_info(self):
        return {
            'Contact-Name': self.submitter.get_full_name(),
            'Contact-Email': self.submitter.email,
            'Author': self.codebase.contributor_list,
            'Version-Number': self.version_number,
            'Codebase-DOI': str(self.codebase.doi),
            'DOI': str(self.doi),
            # FIXME: check codemeta for additional metadata
        }

    def get_or_create_sip_bag(self):
        return fs.make_bag(str(self.submitted_package_path()), self.bagit_info)

    def save_draft(self):
        self.draft = False
        release = CodebaseRelease.objects.filter(codebase__identifier=self.codebase.identifier, draft=True).first()
        if release:
            self.id = release.id
        self.save()

    def publish(self):
        publisher = CodebaseReleasePublisher(self)
        publisher.publish()

    def __str__(self):
        return '{0} {1} v{2} {3}'.format(self.codebase, self.submitter.username, self.version_number,
                                         self.submitted_package_path())

    class Meta:
        unique_together = ('codebase', 'version_number')
        permissions = (('view_codebase_release', 'Can view codebase release'),)


class CodebaseReleasePublisher:
    def __init__(self, codebase_release: CodebaseRelease):
        self.codebase_release = codebase_release

    def is_publishable(self):
        if self.codebase_release.contributors.count() < 1:
            raise ValidationError('Must have at least one contributor to publish a release')
        path = self.codebase_release.workdir_path.joinpath('code')
        if path.exists():
            files = os.listdir(str(path))
        else:
            files = []
        if not files:
            raise ValidationError('Must have at least one source file')

    def copy_workdir_to_sip(self):
        shutil.copytree(str(self.codebase_release.workdir_path), str(self.codebase_release.submitted_package_path()))

    def publish(self):
        self.is_publishable()
        self.copy_workdir_to_sip()
        if not self.codebase_release.codebase.live:
            self.codebase_release.codebase.live = True
            self.codebase_release.codebase.save()
        self.codebase_release.live = True
        self.codebase_release.save()


class ReleaseContributor(models.Model):
    release = models.ForeignKey(CodebaseRelease, on_delete=models.CASCADE, related_name='codebase_contributors')
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE, related_name='codebase_contributors')
    include_in_citation = models.BooleanField(default=True)
    roles = ArrayField(models.CharField(
        max_length=100, choices=ROLES, default=ROLES.author,
        help_text=_(
            'Roles from https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode'
        )
    ), default=list)
    index = models.PositiveSmallIntegerField(help_text=_('Ordering field for codebase contributors'))

    def __str__(self):
        return "{0} contributor {1}".format(self.release, self.contributor)
