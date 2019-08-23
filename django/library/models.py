import json
import logging
import os
import pathlib
import uuid
from collections import OrderedDict
from datetime import timedelta
from enum import Enum

import semver
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.cache import cache
from django.core.files.images import ImageFile
from django.core.files.storage import FileSystemStorage
from django.db import models, transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from ipware import get_client_ip
from model_utils import Choices
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from rest_framework.exceptions import ValidationError, UnsupportedMediaType
from taggit.models import TaggedItemBase
from unidecode import unidecode
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.images.models import Image, AbstractImage, AbstractRendition, get_upload_to, ImageQuerySet
from wagtail.search import index
from wagtail.search.backends import get_search_backend
from wagtail.snippets.models import register_snippet

from core import fs
from core.backends import add_to_comses_permission_whitelist
from core.fields import MarkdownField
from core.models import Platform, MemberProfile
from core.queryset import get_viewable_objects_for_user
from core.utils import send_markdown_email
from core.view_helpers import get_search_queryset
from .fs import CodebaseReleaseFsApi, StagingDirectories, FileCategoryDirectories, MessageLevels

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
    ('platform_independent', _('Operating System Independent')),
)


class CodebaseTag(TaggedItemBase):
    content_object = ParentalKey('library.Codebase', related_name='tagged_codebases')


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_languages')


class CodebaseReleasePlatformTag(TaggedItemBase):
    content_object = ParentalKey('library.CodebaseRelease', related_name='tagged_release_platforms')


class ContributorAffiliation(TaggedItemBase):
    content_object = ParentalKey('library.Contributor', related_name='tagged_contributors')


class License(models.Model):
    name = models.CharField(max_length=200, help_text=_('SPDX license code from https://spdx.org/licenses/'))
    url = models.URLField(blank=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.url)


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
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    search_fields = [
        index.SearchField('given_name', partial_match=True, boost=10),
        index.SearchField('family_name', partial_match=True, boost=10),
        index.RelatedFields('affiliations', [
            index.SearchField('name', partial_match=True)
        ]),
        index.SearchField('email', partial_match=True),
        index.RelatedFields('user', [
            index.SearchField('first_name'),
            index.SearchField('last_name'),
            index.SearchField('email'),
            index.SearchField('username'),
        ]),
    ]

    @staticmethod
    def from_user(user):
        return Contributor.objects.get_or_create(
            user=user,
            defaults={
                'given_name': user.first_name,
                'family_name': user.last_name,
                'email': user.email
            }
        )

    @property
    def name(self):
        return self.get_full_name()

    @property
    def orcid_url(self):
        if self.user:
            return self.user.member_profile.orcid_url
        return None

    @property
    def member_profile_url(self):
        if self.user:
            return self.user.member_profile.get_absolute_url()
        return None

    def to_codemeta(self):
        codemeta = {
            '@type': self.type.capitalize(),
            'givenName': self.given_name,
            'familyName': self.family_name,
            'email': self.email,
        }
        if self.orcid_url:
            codemeta['@id'] = self.orcid_url
        return codemeta

    def get_aggregated_search_fields(self):
        return ' '.join({self.given_name, self.family_name, self.email} | self._get_user_fields())

    def _get_user_fields(self):
        if self.user:
            user = self.user
            return {user.first_name, user.last_name, user.username, user.email}
        return set()

    def get_full_name(self, family_name_first=False):
        full_name = ''
        # Bah. Horrid name logic
        if self.type == 'person':
            if family_name_first:
                full_name = '{0}, {1} {2}'.format(self.family_name, self.given_name, self.middle_name)
            elif self.middle_name:
                full_name = '{0} {1} {2}'.format(self.given_name, self.middle_name, self.family_name)
            elif self.given_name:
                if self.family_name:
                    full_name = '{0} {1}'.format(self.given_name, self.family_name)
                else:
                    full_name = self.given_name
            elif self.user:
                full_name = self.user.member_profile.name
            else:
                logger.warning("No usable name found for contributor %s", self.pk)
                return 'No name'
        else:
            full_name = self.given_name
        return full_name.strip()

    @property
    def formatted_affiliations(self):
        return ' '.join(self.affiliations.all())

    def get_profile_url(self):
        user = self.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(reverse('home:profile-list'), urlencode({'query': self.name}))

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
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    referrer = models.URLField(max_length=500, blank=True,
                               help_text=_("captures the HTTP_REFERER if set"))
    release = models.ForeignKey('library.CodebaseRelease', related_name='downloads', on_delete=models.CASCADE)

    def __str__(self):
        return "{0}: downloaded {1}".format(self.ip_address, self.release)

    class Meta:
        indexes = [
            models.Index(fields=['date_created'])
        ]


class CodebaseQuerySet(models.QuerySet):

    def update_publish_date(self):
        for codebase in self.all():
            if codebase.releases.exists():
                first_release = codebase.releases.order_by('first_published_at').first()
                last_release = codebase.releases.order_by('-last_published_on').first()
                codebase.first_published_at = first_release.first_published_at
                codebase.last_published_on = last_release.last_published_on
                codebase.save()

    def update_liveness(self):
        for codebase in self.all():
            codebase.live = codebase.releases.filter(live=True).exists()
            codebase.save()

    def with_viewable_releases(self, user):
        queryset = get_viewable_objects_for_user(user=user, queryset=CodebaseRelease.objects.all())
        return self.prefetch_related(Prefetch('releases', queryset=queryset))

    def with_tags(self):
        return self.prefetch_related('tagged_codebases__tag')

    def with_featured_images(self):
        return self.prefetch_related('featured_images')

    def with_submitter(self):
        return self.select_related('submitter')

    def accessible(self, user):
        return get_viewable_objects_for_user(user=user, queryset=self.with_viewable_releases(user=user))

    def with_contributors(self, release_contributor_qs=None, user=None):
        if user is not None:
            release_qs = get_viewable_objects_for_user(user=user, queryset=CodebaseRelease.objects.all())
            codebase_qs = get_viewable_objects_for_user(user=user, queryset=self)
        else:
            release_qs = CodebaseRelease.objects.public().only('id', 'codebase_id')
            codebase_qs = self.filter(live=True)
        return codebase_qs.prefetch_related(
            Prefetch('releases', release_qs.with_release_contributors(release_contributor_qs)))

    @staticmethod
    def cache_contributors(codebases):
        """Add all_contributors property to all codebases in queryset.

        Returns a list so that it is impossible to call queryset methods on the result and destroy the
        all_contributors property. Should be called after with_contributors for query efficiency. `with_contributors`
        is a seperate function """

        for codebase in codebases:
            codebase.compute_contributors(force=True)

    def public(self):
        """Returns a queryset of all live codebases and their live releases"""
        return self.with_contributors()

    def peer_reviewed(self):
        return self.public().filter(peer_reviewed=True)

    def recently_updated(self, date_filters, **kwargs):
        """ Returns a tuple of three querysets containing new codebases, recently updated codebases, and
        all releases matching the date filters, in order """
        # FIXME: logic might need to be adjusted, updated releases that have been recently modified are not captured
        # (would need to also query on last_modified I think)
        # copy pasted from the curator_statistics.py management command
        releases = CodebaseRelease.objects.filter(**date_filters, **kwargs)

        if 'date_created__range' in date_filters:
            updated_releases = CodebaseRelease.objects.exclude(date_created__gte=date_filters['date_created__range'][0])
        else:
            updated_releases = CodebaseRelease.objects.exclude(**date_filters)
        new_codebases = self.public().filter(
            releases__in=releases
        ).exclude(releases__in=updated_releases).distinct().order_by('title')
        updated_codebases = self.public().filter(
            releases__in=releases).filter(
            releases__in=updated_releases).distinct().order_by('title')
        return new_codebases, updated_codebases, releases


@add_to_comses_permission_whitelist
class Codebase(index.Indexed, ClusterableModel):
    """
    Metadata applicable across a set of CodebaseReleases
    """
    # shortname = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=300)
    description = MarkdownField()
    summary = models.CharField(max_length=500, blank=True)

    featured = models.BooleanField(default=False)

    # db cached liveness dependent on live releases
    live = models.BooleanField(default=False)
    # has_draft_release = models.BooleanField(default=False)
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

    latest_version = models.ForeignKey('CodebaseRelease', null=True, related_name='latest_version',
                                       on_delete=models.SET_NULL)

    repository_url = models.URLField(blank=True,
                                     help_text=_('URL to code repository, e.g., https://github.com/comses/wolf-sheep'))
    replication_text = models.TextField(blank=True,
                                        help_text=_('URL / DOI / citation for the original model being replicated'))
    # FIXME: original Drupal data was stored as text fields -
    # after catalog integration remove these / replace with M2M relationships to Publication entities
    # publication metadata
    references_text = models.TextField(blank=True, help_text=_("Reference DOI / Citations"))
    associated_publication_text = models.TextField(blank=True, help_text=_(
        "DOI / URL / citation to publication associated with this codebase."))
    tags = ClusterTaggableManager(through=CodebaseTag)
    # evaluate this JSONField as an add-anything way to record relationships between this Codebase and other entities
    # with URLs / resolvable identifiers
    relationships = JSONField(default=list)

    # JSONField list of image metadata records with paths referring to self.media_dir()
    media = JSONField(default=list,
                      help_text=_("JSON metadata dict of media associated with this Codebase"))

    submitter = models.ForeignKey(User, related_name='codebases', on_delete=models.PROTECT)

    objects = CodebaseQuerySet.as_manager()

    search_fields = [
        index.SearchField('title', partial_match=True, boost=10),
        index.SearchField('description', partial_match=True),
        index.SearchField('concatenated_tags', partial_match=True),
        index.FilterField('peer_reviewed'),
        index.FilterField('featured'),
        index.FilterField('is_replication'),
        index.FilterField('live'),
        index.FilterField('first_published_at'),
        index.FilterField('last_published_on'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
        index.SearchField('get_all_contributors_search_fields'),
        index.SearchField('references_text', partial_match=True),
        index.SearchField('associated_publication_text', partial_match=True),
    ]

    HAS_PUBLISHED_KEY = True

    @property
    def concatenated_tags(self):
        return ' '.join(self.tags.values_list('name', flat=True))

    @property
    def deletable(self):
        return not self.live

    @staticmethod
    def _release_upload_path(instance, filename):
        return str(pathlib.Path(instance.codebase.upload_path, filename))

    def as_featured_content_dict(self):
        return dict(
            title=self.title,
            summary=self.summarized_description,
            codebase_image=self.get_featured_image(),
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
        return pathlib.Path(settings.LIBRARY_ROOT, str(self.uuid), 'media', *args)

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
    def codebase_contributors_redis_key(self):
        return 'codebase:contributors:{0}'.format(self.identifier)

    def compute_contributors(self, force=False):
        redis_key = self.codebase_contributors_redis_key
        codebase_contributors = cache.get(redis_key) if not force else None

        if codebase_contributors is None:
            codebase_contributors_dict = OrderedDict()
            for release in self.releases.prefetch_related('codebase_contributors').all():
                for release_contributor in release.codebase_contributors.select_related(
                        'contributor__user__member_profile').order_by('index'):
                    contributor = release_contributor.contributor
                    codebase_contributors_dict[contributor] = None
            # PEP 448 syntax to unpack dict keys into list literal
            # https://www.python.org/dev/peps/pep-0448/
            codebase_contributors = [*codebase_contributors_dict]
            cache.set(redis_key, codebase_contributors)
        return codebase_contributors

    @property
    def all_contributors(self):
        """Get all the contributors associated with this codebase. A contributor is associated
        with a codebase if any release associated with that codebase is also associated with the
        same contributor.

        Caching contributors on _all_contributors makes it possible to ask for
        codebase_contributors in bulk"""
        if not hasattr(self, '_all_contributors'):
            self._all_contributors = self.compute_contributors()
        return self._all_contributors

    @property
    def contributor_list(self):
        contributor_list = [c.get_full_name(family_name_first=True) for c in self.all_contributors]
        return contributor_list

    def get_all_contributors_search_fields(self):
        return ' '.join([c.get_aggregated_search_fields() for c in self.all_contributors])

    def download_count(self):
        return CodebaseReleaseDownload.objects.filter(release__codebase__id=self.pk).count()

    def ordered_releases(self, has_change_perm=False, **kwargs):
        releases = self.releases.order_by('-version_number').filter(**kwargs)
        return releases if has_change_perm else releases.exclude(live=False)

    @classmethod
    def get_list_url(cls):
        return reverse('library:codebase-list')

    @staticmethod
    def format_doi_url(doi_string):
        return 'https://doi.org/{0}'.format(doi_string) if doi_string else ''

    def get_absolute_url(self):
        return reverse('library:codebase-detail', kwargs={'identifier': self.identifier})

    def get_draft_url(self):
        return reverse('library:codebaserelease-draft', kwargs={'identifier': self.identifier})

    def media_url(self, name):
        return '{0}/media/{1}'.format(self.get_absolute_url(), name)

    @property
    def doi_url(self):
        return Codebase.format_doi_url(self.doi)

    def get_all_next_possible_version_numbers(self, minor_only=False):
        if self.releases.all():
            possible_version_numbers = set()
            for release in self.releases.all():
                possible_version_numbers.update(release.possible_next_versions(minor_only))
            for release in self.releases.all():
                possible_version_numbers.discard(release.version_number)
            return possible_version_numbers
        else:
            return {'1.0.0', }

    def next_version_number(self, version_number=None):
        if version_number is None:
            possible_version_numbers = self.get_all_next_possible_version_numbers(minor_only=True)
            max_version_number = '1.0.0'
            for version_number in possible_version_numbers:
                max_version_number = semver.max_ver(max_version_number, version_number)
            version_number = max_version_number
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
        if 'draft' not in kwargs:
            kwargs['draft'] = False
        if 'live' not in kwargs:
            kwargs['live'] = True
        release = CodebaseRelease.objects.create(
            submitter_id=submitter_id,
            version_number=version_number,
            identifier=identifier,
            codebase=self,
            **kwargs)
        if submitted_package:
            release.submitted_package.save(submitted_package.name, submitted_package, save=False)
        if release.is_published:
            self.latest_version = release
            self.save()
        return release

    def import_media(self, fileobj, user=None, title=None, images_only=True):
        if user is None:
            user = self.submitter

        name = os.path.basename(fileobj.name)

        if title is None:
            title = name or self.title

        path = self.media_dir(name)
        os.makedirs(str(path.parent), exist_ok=True)
        with path.open('wb') as f:
            f.write(fileobj.read())

        is_image = fs.is_image(str(path))
        if not is_image and images_only:
            logger.info('removing non image file: %s', path)
            path.unlink()
            raise UnsupportedMediaType(fs.mimetypes.guess_type(name)[0], detail='{} is not an image'.format(name))
        image_metadata = {
            'name': name,
            'path': str(self.media_dir()),
            'mimetype': fs.mimetypes.guess_type(str(path)),
            'url': self.media_url(name),
            'featured': is_image,
        }

        logger.info('featured image: %s', image_metadata)
        if image_metadata['featured']:
            filename = image_metadata['name']
            path = pathlib.Path(image_metadata['path'], filename)
            image = CodebaseImage(codebase=self,
                                  title=title,
                                  file=ImageFile(path.open('rb')),
                                  uploaded_by_user=user)
            image.save()
            self.featured_images.add(image)
            logger.info('added featured image')
            return image
        else:
            self.media.append(image_metadata)
            return image_metadata

    @transaction.atomic
    def get_or_create_draft(self):
        draft = self.releases.filter(draft=True).first()
        if not draft:
            draft = self.create_release()
        return draft

    def create_release(self, initialize=True, **overrides):
        # FIXME: guard against not creating a new draft if there's an existing unpublished release, see
        # https://github.com/comses/comses.net/issues/304
        submitter = self.submitter
        version_number = self.next_version_number()
        previous_release = self.releases.last()
        release_metadata = dict(
            submitter=submitter,
            version_number=version_number,
            identifier=None,
            live=False,
            draft=True,
            share_uuid=uuid.uuid4())
        if previous_release is None:
            release_metadata['codebase'] = self
            release_metadata.update(overrides)
            release = CodebaseRelease.objects.create(**release_metadata)
            # add submitter as a release contributor automatically
            # https://github.com/comses/core.comses.net/issues/129
            release.add_contributor(self.submitter)
        else:
            # copy previous release metadata
            previous_release_contributors = ReleaseContributor.objects.filter(release_id=previous_release.id)
            previous_release.id = None
            release = previous_release
            for k, v in release_metadata.items():
                setattr(release, k, v)
            release.doi = None
            release.save()
            previous_release_contributors.copy_to(release)

        if initialize:
            fs_api = release.get_fs_api()
            fs_api.initialize()
        if release.is_published:
            self.latest_version = release
            self.save()
        return release

    @classmethod
    def elasticsearch_query(cls, text):
        document_type = get_search_backend().get_index_for_model(cls).mapping_class(cls).get_document_type()
        return {
            "bool": {
                "must": [
                    {
                        "match": {
                            "_all": text
                        }
                    }
                ],
                "filter": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "live_filter": True
                                }
                            },
                            {
                                "type": {
                                    "value": document_type
                                }
                            }
                        ]
                    }
                }
            }
        }

    def __str__(self):
        return "{0} {1} identifier={2} live={3}".format(self.title,
                                                        self.date_created,
                                                        str(self.identifier),
                                                        self.live)


class CodebaseImageQuerySet(ImageQuerySet):
    def accessible(self, user):
        return self.filter(uploaded_by_user=user)


class CodebaseImage(AbstractImage):
    codebase = models.ForeignKey(Codebase, related_name='featured_images', on_delete=models.CASCADE)
    file = models.ImageField(
        verbose_name=_('file'), upload_to=get_upload_to, width_field='width', height_field='height',
        storage=FileSystemStorage(location=settings.LIBRARY_ROOT)
    )

    admin_form_fields = Image.admin_form_fields + ('codebase',)

    objects = CodebaseImageQuerySet.as_manager()

    def get_upload_to(self, filename):
        # adapted from wagtailimages/models
        folder_name = str(self.codebase.media_dir())
        filename = self.file.field.storage.get_valid_name(filename)

        # do a unidecode in the filename and then
        # replace non-ascii characters in filename with _ , to sidestep issues with filesystem encoding
        filename = "".join((i if ord(i) < 128 else '_') for i in unidecode(filename))

        # Truncate filename so it fits in the 100 character limit
        # https://code.djangoproject.com/ticket/9893
        full_path = os.path.join(folder_name, filename)
        if len(full_path) >= 95:
            chars_to_trim = len(full_path) - 94
            prefix, extension = os.path.splitext(filename)
            filename = prefix[:-chars_to_trim] + extension
            full_path = os.path.join(folder_name, filename)

        return full_path


class CodebaseRendition(AbstractRendition):
    image = models.ForeignKey(CodebaseImage, related_name='renditions', on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('image', 'filter_spec', 'focal_point_key'),
        )


""" FIXME: disabled until citation migrates to django 2.0
class CodebasePublication(models.Model):
    release = models.ForeignKey('library.CodebaseRelease', on_delete=models.CASCADE)
    publication = models.ForeignKey('citation.Publication', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    index = models.PositiveIntegerField(default=1)
"""


class CodebaseReleaseQuerySet(models.QuerySet):
    def with_release_contributors(self, release_contributor_qs=None, user=None):
        if release_contributor_qs is None:
            release_contributor_qs = ReleaseContributor.objects.only('id', 'contributor_id', 'release_id')

        contributor_qs = Contributor.objects.prefetch_related('user').prefetch_related('tagged_contributors__tag')
        release_contributor_qs = release_contributor_qs.prefetch_related(
            Prefetch('contributor', contributor_qs))

        return self.prefetch_related(Prefetch('codebase_contributors', release_contributor_qs))

    def with_platforms(self):
        return self.prefetch_related('tagged_release_platforms__tag')

    def with_programming_languages(self):
        return self.prefetch_related('tagged_release_languages__tag')

    def with_codebase(self):
        return self.prefetch_related(
            models.Prefetch('codebase', Codebase.objects.with_tags().with_featured_images()))

    def with_submitter(self):
        return self.prefetch_related('submitter')

    def public(self):
        return self.filter(draft=False).filter(live=True)

    def accessible_without_codebase(self, user):
        return get_viewable_objects_for_user(user, queryset=self)

    def accessible(self, user):
        return get_viewable_objects_for_user(user, queryset=self)

    def latest_for_feed(self, number=10, include_all=False):
        qs = self.public().select_related('codebase', 'submitter__member_profile').annotate(
            description=models.F('codebase__description')
        ).order_by('-date_created')
        if include_all:
            return qs
        return qs[:number]


@add_to_comses_permission_whitelist
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
    first_published_at = models.DateTimeField(null=True, blank=True)
    last_published_on = models.DateTimeField(null=True, blank=True)

    peer_reviewed = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)
    share_uuid = models.UUIDField(default=None, blank=True, null=True, unique=True)
    identifier = models.CharField(max_length=128, unique=True, null=True)
    doi = models.CharField(max_length=128, unique=True, null=True)
    license = models.ForeignKey(License, null=True, on_delete=models.SET_NULL)
    release_notes = MarkdownField(blank=True,
                                  max_length=2048,
                                  help_text=_('Markdown formattable text, e.g., run conditions'))
    summary = models.CharField(max_length=1000, blank=True)
    documentation = models.FileField(null=True, help_text=_('Fulltext documentation file (PDF/PDFA)'))
    embargo_end_date = models.DateTimeField(null=True, blank=True)
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
    platforms = models.ManyToManyField(Platform)
    programming_languages = ClusterTaggableManager(through=ProgrammingLanguage,
                                                   related_name='pl_codebase_releases')
    codebase = models.ForeignKey(Codebase, related_name='releases', on_delete=models.PROTECT)
    submitter = models.ForeignKey(User, related_name='releases', on_delete=models.PROTECT)
    contributors = models.ManyToManyField(Contributor, through='ReleaseContributor')
    submitted_package = models.FileField(upload_to=Codebase._release_upload_path, max_length=1000, null=True,
                                         storage=FileSystemStorage(location=settings.LIBRARY_ROOT))
    # M2M relationships for publications, disabled until citation migrates to django 2.0
    # https://github.com/comses/citation/issues/20
    """
    publications = models.ManyToManyField(
        'citation.Publication',
        through=CodebasePublication,

        related_name='releases',
        help_text=_('Publications on this work'))
    references = models.ManyToManyField('citation.Publication',
                                        related_name='codebase_references',
                                        help_text=_('Related publications'))
    """

    objects = CodebaseReleaseQuerySet.as_manager()

    search_fields = [
        index.SearchField('release_notes'),
        index.SearchField('summary'),
        index.FilterField('os'),
        index.FilterField('first_published_at'),
        index.FilterField('last_published_on'),
        index.FilterField('last_modified'),
        index.FilterField('peer_reviewed'),
        index.FilterField('flagged'),
        index.RelatedFields('platforms', [
            index.SearchField('name'),
            index.SearchField('get_all_tags'),
        ]),
        index.RelatedFields('contributors', [
            index.SearchField('get_aggregated_search_fields'),
        ]),
    ]

    def regenerate_share_uuid(self):
        self.share_uuid = uuid.uuid4()
        self.save()

    def get_edit_url(self):
        return reverse('library:codebaserelease-edit', kwargs={'identifier': self.codebase.identifier,
                                                               'version_number': self.version_number})

    def get_list_url(self):
        return reverse('library:codebaserelease-list', kwargs={'identifier': self.codebase.identifier})

    def get_absolute_url(self):
        return reverse('library:codebaserelease-detail',
                       kwargs={'identifier': self.codebase.identifier, 'version_number': self.version_number})

    def get_request_peer_review_url(self):
        return reverse('library:codebaserelease-request-peer-review',
                       kwargs={'identifier': self.codebase.identifier, 'version_number': self.version_number})

    def get_download_url(self):
        return reverse('library:codebaserelease-download',
                       kwargs={'identifier': self.codebase.identifier, 'version_number': self.version_number})

    def get_notify_reviewers_of_changes_url(self):
        return reverse('library:codebaserelease-notify-reviewers-of-changes',
                       kwargs={'identifier': self.codebase.identifier,
                               'version_number': self.version_number})

    def get_review(self):
        return getattr(self, 'review', None)

    def get_review_status_display(self):
        review = self.get_review()
        if review:
            return review.get_simplified_status_display()
        return 'Artifacts have not been reviewed'

    def get_review_download_url(self):
        if not self.share_uuid:
            self.regenerate_share_uuid()
        return reverse('library:codebaserelease-share-download', kwargs={'share_uuid': self.share_uuid})

    def verify_metadata(self):
        if self.license is None or self.os is None or self.programming_languages.exists() or self.os.exists():
            return False
        else:
            return True

    @property
    def share_url(self):
        if not self.share_uuid:
            self.regenerate_share_uuid()
        return reverse('library:codebaserelease-share-detail', kwargs={'share_uuid': self.share_uuid})

    @property
    def regenerate_share_url(self):
        return reverse('library:codebaserelease-regenerate-share-uuid',
                       kwargs={'identifier': self.codebase.identifier,
                               'version_number': self.version_number})

    @property
    def is_peer_review_requestable(self):
        """
        Returns true if this release has not already been peer reviewed and a related PeerReview does not exist
        """
        return not self.peer_reviewed and self.get_review() is None and self.verify_metadata()

    @property
    def is_latest_version(self):
        return self.version_number == self.codebase.latest_version.version_number

    @property
    def doi_url(self):
        return Codebase.format_doi_url(self.doi)

    @property
    def permanent_url(self):
        if self.doi:
            return self.doi_url
        return '{0}{1}'.format(settings.BASE_URL, self.get_absolute_url())

    @property
    def citation_text(self):
        if not self.last_published_on:
            return 'This model must be published first in order to be citable.'

        authors = ', '.join(self.contributor_list)
        return '{authors} ({publish_date}). "{title}" (Version {version}). _{cml}_. Retrieved from: {purl}'.format(
            authors=authors,
            publish_date=self.last_published_on.strftime('%Y, %B %d'),
            title=self.codebase.title,
            version=self.version_number,
            cml='CoMSES Computational Model Library',
            purl=self.permanent_url
        )

    def download_count(self):
        return self.downloads.count()

    @transaction.atomic
    def record_download(self, request):
        referrer = request.META.get('HTTP_REFERER', '')
        client_ip, is_routable = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        self.downloads.create(user=user, referrer=referrer, ip_address=client_ip)

    @property
    def title(self):
        return '{} v{}'.format(self.codebase.title,
                               self.version_number)

    @property
    def archive_filename(self):
        return '{0}_v{1}.zip'.format(slugify(self.codebase.title), self.version_number)

    @property
    def contributor_list(self):
        return [c.contributor.get_full_name(family_name_first=True) for c in self.index_ordered_release_contributors]

    @property
    def index_ordered_release_contributors(self):
        return self.codebase_contributors.order_by('index')

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

    def codemeta_authors(self):
        return [author.contributor.to_codemeta() for author in ReleaseContributor.objects.authors(self)]

    def codemeta_programming_languages(self):
        return [{'@type': 'ComputerLanguage', 'name': pl.name} for pl in self.programming_languages.all()]

    @property
    def codemeta(self):
        # FIXME: probably DEFAULT_CODEMETA_DATA belongs here instead and fs_api should refer to it
        metadata = self.get_fs_api().DEFAULT_CODEMETA_DATA.copy()
        metadata.update(
            identifier=str(self.codebase.uuid),
            license=self.license.url,
            description=self.codebase.description.raw,
            version=self.version_number,
            programmingLanguage=self.codemeta_programming_languages(),
            author=self.codemeta_authors(),
        )
        return metadata

    @property
    def is_published(self):
        return self.live and not self.draft

    def get_fs_api(self, mimetype_mismatch_message_level=MessageLevels.error) -> CodebaseReleaseFsApi:
        fs_api = CodebaseReleaseFsApi(uuid=self.codebase.uuid, identifier=self.codebase.identifier,
                                      version_number=self.version_number, release_id=self.id,
                                      mimetype_mismatch_message_level=mimetype_mismatch_message_level)
        fs_api.initialize()
        return fs_api

    def add_contributor(self, submitter):
        contributor, created = Contributor.from_user(submitter)
        self.codebase_contributors.create(contributor=contributor, roles=[ROLES.author], index=0)

    @transaction.atomic
    def publish(self):
        CodebaseReleasePublisher(self).publish()

    # FIXME: use semver.bump_version instead of this handrolled logic
    def possible_next_versions(self, minor_only=False):
        major, minor, patch = [int(v) for v in self.version_number.split('.')]
        next_minor = '{}.{}.0'.format(major, minor + 1)
        if minor_only:
            return {next_minor, }
        next_major = '{}.0.0'.format(major + 1)
        next_bugfix = '{}.{}.{}'.format(major, minor, patch + 1)
        return {next_major, next_minor, next_bugfix}

    def get_allowed_version_numbers(self):
        codebase = Codebase.objects.prefetch_related(
            Prefetch('releases', CodebaseRelease.objects.exclude(id=self.id))
        ).get(id=self.codebase_id)
        return codebase.get_all_next_possible_version_numbers()

    def set_version_number(self, version_number):
        if self.is_published:
            raise ValidationError({'non_field_errors': ['Cannot set version number on published release']})
        try:
            semver.parse(version_number)
        except ValueError:
            raise ValidationError({'version_number': ['Version number not a valid semantic version string']})
        not_allowed_version_numbers = CodebaseRelease.objects.filter(codebase=self.codebase).exclude(id=self.id) \
            .order_by('version_number').values_list('version_number', flat=True)
        if version_number in not_allowed_version_numbers:
            raise ValidationError({'version_number': ["Another release has version number. Please select another"]})
        self.version_number = version_number

    def __str__(self):
        return '{0} {1} v{2}'.format(self.codebase, self.submitter.username, self.version_number)

    class Meta:
        unique_together = ('codebase', 'version_number')


class CodebaseReleasePublisher:
    def __init__(self, codebase_release: CodebaseRelease):
        self.codebase_release = codebase_release

    def is_publishable(self):
        fs_api = self.codebase_release.get_fs_api()
        storage = fs_api.get_stage_storage(StagingDirectories.sip)
        code_msg = self.has_files(storage, FileCategoryDirectories.code)
        docs_msg = self.has_files(storage, FileCategoryDirectories.docs)
        msg = ' '.join(m for m in [code_msg, docs_msg] if m)
        if msg:
            raise ValidationError(msg)

    def has_files(self, storage, category: FileCategoryDirectories):
        if storage.exists(category.name):
            code_files = list(storage.list(category))
        else:
            code_files = []
        if not code_files:
            return 'Must have at least one {} file.'.format(category.name)
        else:
            return ''

    def publish(self):
        if not self.codebase_release.live:
            self.is_publishable()
            now = timezone.now()
            self.codebase_release.first_published_at = now
            self.codebase_release.last_published_on = now
            self.codebase_release.live = True
            self.codebase_release.draft = False
            fs_api = self.codebase_release.get_fs_api()
            fs_api.get_or_create_sip_bag(self.codebase_release.bagit_info)
            fs_api.build_aip()
            fs_api.build_archive()
            self.codebase_release.save()

            codebase = self.codebase_release.codebase

            codebase.latest_version = self.codebase_release
            codebase.live = True
            codebase.last_published_on = now
            if codebase.first_published_at is None:
                codebase.first_published_at = now
            codebase.save()


class ReleaseContributorQuerySet(models.QuerySet):

    def copy_to(self, release: CodebaseRelease):
        release_contributors = list(self)
        for release_contributor in release_contributors:
            release_contributor.pk = None
            release_contributor.release = release
        return self.bulk_create(release_contributors)

    def authors(self, release):
        qs = self.select_related('contributor').filter(
            release=release, include_in_citation=True, roles__contains='{author}'
        )
        return qs.order_by('index')


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

    objects = ReleaseContributorQuerySet.as_manager()

    def __str__(self):
        return "{0} contributor {1}".format(self.release, self.contributor)


class ChoicesMixin(Enum):
    @classmethod
    def to_choices(cls):
        return Choices(*((choice.name, choice.value) for choice in cls))

    @classmethod
    def to_dict(cls):
        return {level.name: str(level.value) for level in cls}

    @classmethod
    def to_json(cls):
        return json.dumps(cls.to_dict())


class ReviewerRecommendation(ChoicesMixin, Enum):
    accept = _('This computational model meets CoMSES Net peer review requirements.')
    revise = _('This computational model must be revised to meet CoMSES Net peer review requirements.')


class ReviewStatus(ChoicesMixin, Enum):
    """
    Review status represents the aggregate status of the review.

    Used by the editor, author and reviewer to determine who has to respond and if the review is complete
    """

    # No reviewer has given feedback
    awaiting_reviewer_feedback = _('Awaiting reviewer feedback')
    # At least one reviewer has provided feedback on a model and an editor has not requested changes
    # to the model
    awaiting_editor_feedback = _('Awaiting editor feedback')
    # An editor has requested changes to a model. The author has either not given changes or
    # given changes that the editor has not approved of yet or has asked further revisions on
    awaiting_author_changes = _('Awaiting author release changes')
    # The model review process is complete
    complete = _('Review is complete')

    @property
    def is_pending(self):
        return self != ReviewStatus.complete

    @property
    def is_complete(self):
        return self == ReviewStatus.complete

    @property
    def is_awaiting_author_changes(self):
        return self == ReviewStatus.awaiting_author_changes

    @property
    def is_awaiting_editor_feedback(self):
        return self == ReviewStatus.awaiting_editor_feedback

    @property
    def simple_display_message(self):
        return 'Peer review in process' if self.is_pending else 'Peer reviewed'


class PeerReviewEvent(ChoicesMixin, Enum):
    """
    The review event represents events that have occurred on a review.

    Used by the editor to understand the history of changes applied to the models
    """

    invitation_sent = _('Reviewer has been invited')
    invitation_resent = _('Reviewer invitation has been resent')
    invitation_accepted = _('Reviewer has accepted invitation')
    invitation_declined = _('Reviewer has declined invitation')
    reviewer_feedback_submitted = _('Reviewer has given feedback')
    author_resubmitted = _('Author has resubmitted release for review')
    review_status_updated = _('Editor manually changed review status')
    revisions_requested = _('Editor has requested revisions to this release')
    release_certified = _('Editor has taken reviewer feedback into account and certified this release as peer reviewed')


class PeerReviewQuerySet(models.QuerySet):

    def find_candidate_reviewers(self, query=None):
        # TODO: return a MemberProfile queryset annotated with number of invitations, accepted invitations, and completed
        # reviews
        # invited_reviewers_qs = PeerReviewInvitation.objects.candidate_reviewers()
        """
        raw_query = ('SELECT mp.id, sum(case when pri.id is not null and pri.accepted is null then 1 else 0 end) as n_unresponded_invitations, '
                     'sum(case when pri.accepted=false then 1 else 0 end) as n_declined_invitations, '
                     'sum(case when pri.accepted=true then 1 else 0 end) as n_accepted_invitations '
                     'FROM library_peerreviewinvitation pri RIGHT JOIN core_memberprofile mp ON pri.candidate_reviewer_id=mp.id '
                     'INNER JOIN auth_user u on mp.user_id=u.id '
                     'WHERE u.is_active=true AND u.id > 2 '
                     'GROUP BY mp.id;')
        """

        queryset = MemberProfile.objects.public()
        return get_search_queryset(query, queryset)


@register_snippet
class PeerReview(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=ReviewStatus.to_choices(),
                              default=ReviewStatus.awaiting_reviewer_feedback.name,
                              help_text=_("The current status of this review."),
                              max_length=32)
    codebase_release = models.OneToOneField(CodebaseRelease, related_name='review', on_delete=models.PROTECT)
    submitter = models.ForeignKey(MemberProfile, related_name='+', on_delete=models.PROTECT)
    slug = models.UUIDField(default=uuid.uuid4, unique=True, null=True)

    objects = PeerReviewQuerySet.as_manager()

    panels = [
        FieldPanel('status'),
    ]

    @property
    def is_complete(self):
        return self.get_status().is_complete

    @property
    def is_awaiting_author_changes(self):
        return self.get_status().is_awaiting_author_changes

    @property
    def is_awaiting_reviewer_changes(self):
        return self.get_status().is_awaiting_reviewer_changes

    def get_status(self):
        return ReviewStatus[self.status]

    def get_simplified_status_display(self):
        return self.get_status().simple_display_message

    def get_edit_url(self):
        return reverse('library:profile-edit', kwargs={'user_pk': self.user.pk})

    def get_invite(self, member_profile):
        return self.invitation_set.filter(candidate_reviewer=member_profile).first()

    @transaction.atomic
    def get_absolute_url(self):
        if not self.slug:
            self.slug = uuid.uuid4()
            self.save()
        return reverse('library:peer-review-detail', kwargs={'slug': self.slug})

    def get_event_list_url(self):
        return reverse('library:peer-review-event-list', kwargs={'slug': self.slug})

    @transaction.atomic
    def set_complete_status(self, editor: MemberProfile):
        self.set_status(ReviewStatus.complete)
        self.save()
        self.log(
            author=editor,
            action=PeerReviewEvent.release_certified,
            message='Model has been certified as peer reviewed'
        )
        self.codebase_release.peer_reviewed = True
        self.codebase_release.save()

        # FIXME: consider moving this into explicit send_model_certified_email()
        send_markdown_email(
            subject='[CoMSES Net] Peer review completed',
            template_name='library/review/email/model_certified.jinja',
            context={'review': self},
            to=[self.submitter.email],
            bcc=[editor.email]
        )

    def log(self, message: str, action: PeerReviewEvent, author: MemberProfile):
        return self.event_set.create(message=message, action=action.name, author=author)

    def set_status(self, status: ReviewStatus):
        self.status = status.name

    def author_resubmitted_changes(self, changes_made=None):
        author = self.submitter
        self.log(message='Release has been resubmitted for review: {}'.format(changes_made),
                 action=PeerReviewEvent.author_resubmitted,
                 author=author)
        self.send_author_updated_content_email()

    def send_author_updated_content_email(self):
        qs = self.invitation_set.filter(accepted=True)
        # if there are no currently accepted invitations, status should be set to awaiting editor feedback
        _status = ReviewStatus.awaiting_reviewer_feedback if qs.exists() else ReviewStatus.awaiting_editor_feedback
        self.set_status(_status)
        for invitation in qs:
            invitation.send_author_resubmitted_email()
        self.save()

    def send_author_requested_peer_review_email(self):
        send_markdown_email(
            subject='[CoMSES Net] New peer review request',
            template_name='library/review/email/review_requested.jinja',
            context={'review': self},
            to=[settings.EDITOR_EMAIL]
        )

    @property
    def status_levels(self):
        return [{'value': choice[0], 'label': str(choice[1])} for choice in ReviewStatus.to_choices()]

    @property
    def title(self):
        return self.codebase_release.title

    def __str__(self):
        return 'PeerReview of {} requested on {}. Status: {}, last modified {}'.format(
            self.title,
            self.date_created,
            self.get_status_display(),
            self.last_modified
        )


class PeerReviewInvitationQuerySet(models.QuerySet):

    def accepted(self, **kwargs):
        return self.filter(accepted=True, **kwargs)

    def declined(self, **kwargs):
        return self.filter(accepted=False, **kwargs)

    def pending(self, **kwargs):
        return self.filter(accepted__isnull=True, **kwargs)

    def candidate_reviewers(self, **kwargs):
        # FIXME: fairly horribly inefficient
        return MemberProfile.objects.filter(pk__in=self.values_list('candidate_reviewer', flat=True))

    def with_reviewer_statistics(self):
        return self.prefetch_related(models.Prefetch('candidate_reviewer', PeerReview.objects.find_candidate_reviewers()))


@register_snippet
class PeerReviewInvitation(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    review = models.ForeignKey(PeerReview, related_name='invitation_set', on_delete=models.CASCADE)
    editor = models.ForeignKey(MemberProfile, related_name='+', on_delete=models.PROTECT)
    candidate_reviewer = models.ForeignKey(MemberProfile,
                                           related_name='peer_review_invitation_set',
                                           on_delete=models.CASCADE)
    optional_message = MarkdownField(help_text=_("Optional markdown text to be added to the email"))
    slug = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    accepted = models.NullBooleanField(
        verbose_name=_("Invitation status"),
        choices=Choices(
            (None, _('Waiting for response')),
            (False, _('Decline')),
            (True, _('Accept')),
        ),
        help_text=_('Accept or decline this peer review invitation')
    )

    objects = PeerReviewInvitationQuerySet.as_manager()

    @property
    def latest_feedback(self):
        if not self.feedback_set.exists():
            return self.feedback_set.create()
        return self.feedback_set.last()

    @property
    def expiration_date(self):
        return self.date_created + timedelta(days=settings.PEER_REVIEW_INVITATION_EXPIRATION)

    @property
    def is_expired(self):
        return timezone.now() > self.expiration_date

    @property
    def reviewer_email(self):
        return self.candidate_reviewer.email

    @property
    def editor_email(self):
        return self.editor.email

    @property
    def invitee(self):
        return self.candidate_reviewer.name

    @property
    def from_email(self):
        return settings.DEFAULT_FROM_EMAIL

    @transaction.atomic
    def send_author_resubmitted_email(self):
        if not self.accepted:
            logger.error("Trying to send an author resubmitted notification to an unaccepted invitation - ignoring.")
            return
        send_markdown_email(
            subject='[CoMSES Net] Peer review: updates to release {}'.format(self.review.title),
            template_name='library/review/email/author_updated_content_for_reviewer_email.jinja',
            context={
                'invitation': self,
                # create a fresh feedback object for the reviewer to edit
                'feedback': self.feedback_set.create()
            },
            to=[self.reviewer_email],
            cc=[self.editor_email],
        )

    @transaction.atomic
    def send_candidate_reviewer_email(self, resend=False):
        send_markdown_email(
            subject='[CoMSES Net] Peer review: Request to review a computational model',
            template_name='library/review/email/review_invitation.jinja',
            context={'invitation': self},
            to=[self.reviewer_email],
            cc=[self.editor_email]
        )
        self.review.log(
            action=PeerReviewEvent.invitation_sent if resend else PeerReviewEvent.invitation_resent,
            author=self.editor,
            message='{} sent an invitation to candidate reviewer {}'.format(
                self.editor, self.candidate_reviewer)
        )

    @transaction.atomic
    def accept(self):
        self.accepted = True
        self.save()
        feedback = self.latest_feedback
        self.review.log(action=PeerReviewEvent.invitation_accepted,
                        author=self.candidate_reviewer,
                        message='Invitation accepted by {}'.format(self.candidate_reviewer))
        send_markdown_email(
            subject='[CoMSES Net] Peer review: accepted invitation to review model',
            template_name='library/review/email/review_invitation_accepted.jinja',
            context={'invitation': self, 'feedback': feedback},
            to=[self.reviewer_email, self.editor.email],
        )
        return feedback

    @transaction.atomic
    def decline(self):
        self.accepted = False
        self.save()
        self.review.log(action=PeerReviewEvent.invitation_declined,
                        author=self.candidate_reviewer,
                        message='Invitation declined by {}'.format(self.candidate_reviewer))
        send_markdown_email(
            subject='[CoMSES Net] Peer review: declined invitation to review model',
            template_name='library/review/email/review_invitation_declined.jinja',
            context={'invitation': self},
            to=[self.editor.email],
        )

    def get_absolute_url(self):
        return reverse('library:peer-review-invitation', kwargs=dict(slug=self.slug))

    class Meta:
        unique_together = (('review', 'candidate_reviewer'),)


@register_snippet
class PeerReviewerFeedback(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    invitation = models.ForeignKey(PeerReviewInvitation, related_name='feedback_set', on_delete=models.CASCADE)
    recommendation = models.CharField(choices=ReviewerRecommendation.to_choices(), max_length=16, blank=True)
    private_reviewer_notes = MarkdownField(
        help_text=_('Private reviewer notes to be sent to and viewed by the CoMSES review editors only.'),
        blank=True
    )
    private_editor_notes = MarkdownField(help_text=_('Private editor notes regarding this peer review'), blank=True)
    notes_to_author = MarkdownField(help_text=_("Editor's notes to be sent to the model author, manually compiled from other reviewer comments."),
                                    blank=True)
    has_narrative_documentation = models.BooleanField(
        default=False,
        help_text=_('Is there sufficiently detailed accompanying narrative documentation? (A checked box indicates that the model has narrative documentation)')
    )
    narrative_documentation_comments = models.TextField(
        help_text=_('Reviewer comments on the narrative documentation'), blank=True
    )
    has_clean_code = models.BooleanField(
        default=False,
        help_text=_('Is the code clean, well-written, and well-commented with consistent formatting? (A checked box indicates that the model code is clean)')
    )
    clean_code_comments = models.TextField(
        help_text=_('Reviewer comments on code cleanliness'), blank=True
    )
    is_runnable = models.BooleanField(
        default=False,
        help_text=_('Were you able to run the model with the provided instructions? (A checked box indicates that the model is runnable)')
    )
    runnable_comments = models.TextField(
        help_text=_('Reviewer comments on running the model with the provided instructions'),
        blank=True
    )
    reviewer_submitted = models.BooleanField(
        help_text=_('Internal field, set to True when the reviewer has finalized their feedback and is ready for an editor to check their submission.'),
        default=False
    )

    def get_absolute_url(self):
        return reverse('library:peer-review-feedback-edit',
                       kwargs={'slug': self.invitation.slug, 'feedback_id': self.id})

    def get_editor_url(self):
        return reverse('library:peer-review-feedback-editor-edit',
                       kwargs={'slug': self.invitation.slug, 'feedback_id': self.id})

    @transaction.atomic
    def reviewer_completed(self):
        """Add a reviewer gave feedback event to the log

        Preconditions:

        reviewer updated feedback
        """
        review = self.invitation.review
        review.set_status(ReviewStatus.awaiting_editor_feedback)
        review.save()
        reviewer = self.invitation.candidate_reviewer
        review.log(
            action=PeerReviewEvent.reviewer_feedback_submitted,
            author=reviewer,
            message='Reviewer {} provided feedback'.format(reviewer)
        )
        send_markdown_email(
            subject='[CoMSES Net] Peer review: reviewer submitted, editor action needed',
            template_name='library/review/email/reviewer_submitted.jinja',
            context={'review': review, 'invitation': self.invitation},
            to=[self.invitation.editor_email],
        )
        send_markdown_email(
            subject='[CoMSES Net] Peer review: feedback submitted',
            template_name='library/review/email/reviewer_submitted_thanks.jinja',
            context={'review': review, 'invitation': self.invitation},
            to=[reviewer.email],
        )

    @transaction.atomic
    def editor_called_for_revisions(self):
        """Add an editor called for revisions event to the log

        Preconditions:

        editor updated feedback
        """
        review = self.invitation.review
        editor = self.invitation.editor
        review.log(
            action=PeerReviewEvent.revisions_requested,
            author=editor,
            message='Editor {} called for revisions'.format(editor)
        )
        review.set_status(ReviewStatus.awaiting_author_changes)
        review.save()
        recipients = {review.submitter.email, review.codebase_release.submitter.email}
        send_markdown_email(
            subject='[CoMSES Net] Peer review: revisions requested',
            template_name='library/review/email/model_revisions_requested.jinja',
            context={'review': review, 'feedback': self},
            to=recipients,
            bcc=[editor.email]
        )

    def __str__(self):
        invitation = self.invitation
        return 'Peer Review Feedback by {}. (submitted? {}) (recommendation: {})'.format(
            invitation.candidate_reviewer,
            self.reviewer_submitted,
            self.get_recommendation_display()
        )


@register_snippet
class PeerReviewEventLog(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    review = models.ForeignKey(PeerReview, related_name='event_set', on_delete=models.CASCADE)
    action = models.CharField(choices=PeerReviewEvent.to_choices(), help_text=_("status action requested."),
                              max_length=32)
    author = models.ForeignKey(MemberProfile, related_name='+', on_delete=models.CASCADE,
                               help_text=_('User originating this action'))
    message = models.CharField(blank=True, max_length=500)

    def add_message(self, message):
        if self.message:
            self.message += '\n\n{}'.format(message)
        else:
            self.message = message
