import json
import logging
import os
import pathlib
import uuid
from collections import OrderedDict
from datetime import timedelta

import semver
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.files.images import ImageFile
from django.core.files.storage import FileSystemStorage
from django.db import models, transaction
from django.db.models import Prefetch, Q, Count, Max
from django.utils.functional import cached_property
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from rest_framework.exceptions import ValidationError, UnsupportedMediaType
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel
from wagtail.coreutils import string_to_ascii
from wagtail.images.models import (
    Image,
    AbstractImage,
    AbstractRendition,
    Filter,
    get_upload_to,
    ImageQuerySet,
)
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from core import fs
from core.backends import add_to_comses_permission_whitelist
from core.fields import MarkdownField
from core.models import Platform, MemberProfile, ModeratedContent
from core.queryset import get_viewable_objects_for_user
from core.utils import send_markdown_email
from core.view_helpers import get_search_queryset
from .fs import (
    CodebaseReleaseFsApi,
    StagingDirectories,
    FileCategoryDirectories,
    MessageLevels,
)

logger = logging.getLogger(__name__)


# Cherry picked from
# https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode
class Role(models.TextChoices):
    AUTHOR = "author", _("Author")
    PUBLISHER = "publisher", _("Publisher")
    CUSTODIAN = "custodian", _("Custodian")
    RESOURCE_PROVIDER = "resourceProvider", _("Resource Provider")
    MAINTAINER = "maintainer", _("Maintainer")
    POINT_OF_CONTACT = "pointOfContact", _("Point of contact")
    EDITOR = "editor", _("Editor")
    CONTRIBUTOR = "contributor", _("Contributor")
    COLLABORATOR = "collaborator", _("Collaborator")
    FUNDER = "funder", _("Funder")
    COPYRIGHT_HOLDER = "copyrightHolder", _("Copyright holder")


class OS(models.TextChoices):
    OTHER = "other", _("Other")
    LINUX = "linux", _("Unix/Linux")
    MACOS = "macos", _("Mac OS")
    WINDOWS = "windows", _("Windows")
    PLATFORM_INDEPENDENT = "platform_independent", _("Operating System Independent")


class CodebaseTag(TaggedItemBase):
    content_object = ParentalKey("library.Codebase", related_name="tagged_codebases")


class ProgrammingLanguage(TaggedItemBase):
    content_object = ParentalKey(
        "library.CodebaseRelease", related_name="tagged_release_languages"
    )


class CodebaseReleasePlatformTag(TaggedItemBase):
    content_object = ParentalKey(
        "library.CodebaseRelease", related_name="tagged_release_platforms"
    )


class ContributorAffiliation(TaggedItemBase):
    content_object = ParentalKey(
        "library.Contributor", related_name="tagged_contributors"
    )


class LicenseQuerySet(models.QuerySet):
    def software(self, **kwargs):
        return self.no_cc(**kwargs)

    def no_cc(self, **kwargs):
        return (
            self.exclude(name="None")
            .exclude(name__istartswith="CC", **kwargs)
            .order_by("name")
        )

    def creative_commons(self, **kwargs):
        return self.filter(name__istartswith="CC", **kwargs)


@register_snippet
class License(models.Model):
    objects = LicenseQuerySet.as_manager()

    name = models.CharField(
        max_length=200, help_text=_("SPDX license code from https://spdx.org/licenses/")
    )
    url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.url})"


class Contributor(index.Indexed, ClusterableModel):
    given_name = models.CharField(
        max_length=100, blank=True, help_text=_("Also doubles as organizational name")
    )
    middle_name = models.CharField(max_length=100, blank=True)
    family_name = models.CharField(max_length=100, blank=True)
    affiliations = ClusterTaggableManager(through=ContributorAffiliation)

    json_affiliations = models.JSONField(
        default=list, help_text=_("JSON-LD list of affiliated institutions")
    )

    type = models.CharField(
        max_length=16,
        choices=(("person", "person"), ("organization", "organization")),
        default="person",
        help_text=_("organizations only use given_name"),
    )
    email = models.EmailField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    search_fields = [
        index.SearchField("given_name"),
        index.SearchField("family_name"),
        index.RelatedFields("affiliations", [index.SearchField("name")]),
        index.SearchField("json_affiliations_string"),
        index.SearchField("email"),
        index.RelatedFields(
            "user",
            [
                index.SearchField("first_name"),
                index.SearchField("last_name"),
                index.SearchField("email"),
                index.SearchField("username"),
            ],
        ),
    ]

    @cached_property
    def json_affiliations_string(self):
        return ", ".join(
            [
                self.to_affiliation_string(affiliation)
                for affiliation in self.json_affiliations
            ]
        )

    @classmethod
    def to_affiliation_string(cls, afl):
        # e.g., "Arizona State University https://www.asu.edu ASU"
        return f"{afl.get('name')} {afl.get('url')} {afl.get('acronym')}"

    @staticmethod
    def from_user(user):
        """
        Returns a tuple of (object, created) based on the
        https://docs.djangoproject.com/en/4.2/ref/models/querysets/#get-or-create
        contract
        """
        try:
            return Contributor.objects.get_or_create(
                user=user,
                defaults={
                    "given_name": user.first_name,
                    "family_name": user.last_name,
                    "email": user.email,
                    # FIXME: rename to affiliations eventually
                    "json_affiliations": user.member_profile.affiliations,
                },
            )
        except Contributor.MultipleObjectsReturned:
            logger.exception(
                "Data integrity issue: found multiple Contributors with the same User %s",
                user,
            )
            return (Contributor.objects.filter(user=user).first(), False)
        except Exception:
            logger.exception("Unable to create Contributor for user %s", user)
            return (None, False)

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

    def get_markdown_link(self):
        return f"[{self.get_full_name()}]({self.member_profile_url})"

    def to_codemeta(self):
        codemeta = {
            "@type": "Person",
            "givenName": self.given_name,
            "familyName": self.family_name,
        }
        # FIXME: should we proxy to User / MemberProfile fields if User is available
        if self.orcid_url:
            codemeta["@id"] = self.orcid_url
        if self.json_affiliations:
            codemeta["affiliation"] = self.codemeta_affiliation
        if self.email:
            codemeta["email"] = self.email
        return codemeta

    def get_aggregated_search_fields(self):
        return " ".join(
            {self.given_name, self.family_name, self.email} | self._get_user_fields()
        )

    def _get_user_fields(self):
        if self.user:
            user = self.user
            return {user.first_name, user.last_name, user.username, user.email}
        return set()

    @property
    def has_name(self):
        return any([self.given_name, self.family_name]) or self.user

    def get_full_name(self, family_name_first=False):
        if self.type == "person":
            return self._get_person_full_name(family_name_first)
        else:
            # organizations only use given_name
            return self.given_name

    def _get_person_full_name(self, family_name_first=False):
        if not self.has_name:
            logger.warning("No usable name found for contributor %s", self.id)
            return ""
        if self.user and not any([self.given_name, self.family_name]):
            return self.user.member_profile.name
        if family_name_first:
            return f"{self.family_name}, {self.given_name} {self.middle_name}".strip()
        else:
            return (
                f"{self.given_name} {self.middle_name}".strip()
                + f" {self.family_name}".rstrip()
            )

    @property
    def formatted_affiliations(self):
        return ", ".join(self.affiliations.values_list("name", flat=True))

    @property
    def codemeta_affiliation(self):
        """
        For now codemeta affiliations appear to be a single https://schema.org/Organization
        """
        if self.json_affiliations:
            return self.to_codemeta_affiliation(self.json_affiliations[0])

    @property
    def primary_affiliation_name(self):
        return self.affiliations.first().name if self.affiliations.exists() else ""

    @property
    def primary_json_affiliation_name(self):
        return self.json_affiliations[0]["name"] if self.json_affiliations else ""

    def to_codemeta_affiliation(self, affiliation):
        if affiliation:
            return {
                # FIXME: may switch to https://schema.org/ResearchOrganization at some point
                "@type": "Organization",
                "@id": affiliation.get("ror_id"),
                "name": affiliation.get("name"),
                "url": affiliation.get("url"),
                "identifier": affiliation.get("ror_id"),
                "sameAs": affiliation.get("ror_id"),
            }
        return {}

    def get_profile_url(self):
        user = self.user
        if user:
            return user.member_profile.get_absolute_url()
        else:
            return "{0}?{1}".format(
                reverse("core:profile-list"), urlencode({"query": self.name})
            )

    def __str__(self):
        if self.email:
            return f"{self.get_full_name()} ({self.email})"
        return self.get_full_name()


class SemanticVersion:
    ALPHA = semver.parse_version_info("0.0.1")
    BETA = semver.parse_version_info("0.1.0")
    DEFAULT = semver.parse_version_info("1.0.0")

    @staticmethod
    def possible_next_versions(version_number, minor_only=False):
        try:
            version_info = semver.parse_version_info(version_number)
        except ValueError:
            version_info = SemanticVersion.DEFAULT
        if minor_only:
            return {
                version_info.bump_minor(),
            }
        return {
            version_info.bump_major(),
            version_info.bump_minor(),
            version_info.bump_patch(),
        }


class CodebaseReleaseDownload(models.Model):
    class Reason(models.TextChoices):
        RESEARCH = "research", _("Research")
        EDUCATION = "education", _("Education")
        COMMERCIAL = "commercial", _("Commercial")
        POLICY = "policy", _("Policy / Planning")
        OTHER = "other", _("Other")

    date_created = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    referrer = models.URLField(
        max_length=500, blank=True, help_text=_("captures the HTTP_REFERER if set")
    )
    release = models.ForeignKey(
        "library.CodebaseRelease", related_name="downloads", on_delete=models.CASCADE
    )
    reason = models.CharField(max_length=500, choices=Reason.choices)
    affiliation = models.JSONField(default=None, null=True)
    industry = models.CharField(max_length=255, choices=MemberProfile.Industry.choices)

    def __str__(self):
        return f"[download] ip: {self.ip_address}, release: {self.release}"

    class Meta:
        indexes = [models.Index(fields=["date_created"])]


class CodebaseQuerySet(models.QuerySet):
    def update_publish_date(self):
        for codebase in self.all():
            if codebase.releases.exists():
                first_release = codebase.releases.order_by("first_published_at").first()
                last_release = codebase.releases.order_by("-last_published_on").first()
                codebase.first_published_at = first_release.first_published_at
                codebase.last_published_on = last_release.last_published_on
                codebase.save()

    def update_liveness(self):
        for codebase in self.all():
            codebase.live = codebase.releases.filter(
                status=CodebaseRelease.Status.PUBLISHED
            ).exists()
            codebase.save()

    def with_viewable_releases(self, user):
        queryset = get_viewable_objects_for_user(
            user=user, queryset=CodebaseRelease.objects.all()
        )
        return self.prefetch_related(Prefetch("releases", queryset=queryset))

    def with_tags(self):
        return self.prefetch_related("tagged_codebases__tag")

    def with_featured_images(self):
        return self.prefetch_related("featured_images")

    def with_submitter(self):
        return self.select_related("submitter")

    def exclude_spam(self):
        # FIXME: duplicated across Event/Job/Codebase querysets
        return self.exclude(is_marked_spam=True)

    def accessible(self, user):
        return get_viewable_objects_for_user(
            user=user, queryset=self.with_viewable_releases(user=user)
        )

    def get_contributor_q(self, user):
        if Contributor.objects.filter(user=user).count() > 1:
            logger.warning("User %s has multiple contributors", user)
        return Q(releases__contributors__user=user)

    def filter_by_contributor(self, user):
        return self.filter(self.get_contributor_q(user)).distinct()

    def filter_by_contributor_or_submitter(self, user):
        return self.filter(Q(submitter=user) | self.get_contributor_q(user)).distinct()

    def with_contributors(self, release_contributor_qs=None, user=None, **kwargs):
        if user is not None:
            release_qs = get_viewable_objects_for_user(
                user=user, queryset=CodebaseRelease.objects.all()
            )
            codebase_qs = get_viewable_objects_for_user(
                user=user, queryset=self.filter(**kwargs)
            )
        else:
            release_qs = CodebaseRelease.objects.public().only("id", "codebase_id")
            codebase_qs = self.filter(live=True, **kwargs)
        return codebase_qs.prefetch_related(
            Prefetch(
                "releases", release_qs.with_release_contributors(release_contributor_qs)
            )
        )

    def with_reviews(self, reviews):
        return (
            self.filter(releases__review__in=reviews)
            .prefetch_related(
                Prefetch(
                    "releases",
                    queryset=CodebaseRelease.objects.filter(review__in=reviews)
                    .select_related("review")
                    .annotate(
                        n_accepted_invites=Count(
                            "review__invitation_set",
                            filter=Q(review__invitation_set__accepted=True),
                        )
                    ),
                )
            )
            .annotate(
                min_n_accepted_invites=Count(
                    "releases__review__invitation_set",
                    filter=Q(releases__review__invitation_set__accepted=True),
                )
            )
            .annotate(max_last_modified=Max("releases__review__last_modified"))
        )

    def public(self, **kwargs):
        """Returns a queryset of all live codebases and their live releases"""
        return self.with_contributors(**kwargs).exclude_spam()

    def peer_reviewed(self):
        return self.public().filter(peer_reviewed=True)

    def updated_after(self, start_date, end_date=None, **kwargs):
        """
        copy pasted and then refactored from the curator_statistics.py management command

        Returns a tuple of three querysets containing new codebases, recently updated codebases, and
        all releases matching the date filters, in that order.

        FIXME: can probably remove the third queryset, we no longer need all releases

        Parameters are a start_date, optional end_date, and arbitrary filters placed in the kwargs (we should probably validate these)

        New codebases are those with releases that were created or published after start_date and before end_date if specified
        Updated codebases are those Codebases created outside the (start_date, end_date) interval but with new CodebaseReleases
        all_releases are all CodebaseReleases that were created or modified within the (start_date, end_date) interval
        """

        # Establish initial querysets
        # new codebases are those created or published after the given start_date
        new_codebases = Codebase.objects.public(**kwargs).filter(
            Q(date_created__gte=start_date) | Q(first_published_at__gte=start_date)
        )
        # updated codebases are those codebases with a last_modified after the start date, sans the new codebases
        updated_codebases = Codebase.objects.public(last_modified__gte=start_date)
        if end_date is None:
            # set today as the default interval end
            end_date = timezone.now().date()
        else:
            # otherwise, apply the filter based on the desired end date over the new and updated codebases
            new_codebases = new_codebases.filter(
                Q(date_created__lte=end_date) & Q(first_published_at__lte=end_date)
            )
            updated_codebases = updated_codebases.filter(last_modified__lte=end_date)
        # remove the new codebases from the updated codebases
        updated_codebases = updated_codebases.difference(new_codebases)
        releases = CodebaseRelease.objects.filter(
            id__in=(
                new_codebases.values_list("releases", flat=True).union(
                    updated_codebases.values_list("releases", flat=True)
                )
            )
        )
        return new_codebases, updated_codebases, releases


@add_to_comses_permission_whitelist
class Codebase(index.Indexed, ModeratedContent, ClusterableModel):
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
    # set to true if any of this Codebase's releases have passed peer review
    peer_reviewed = models.BooleanField(default=False)

    identifier = models.CharField(max_length=128, unique=True)
    doi = models.CharField(max_length=128, unique=True, null=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    latest_version = models.ForeignKey(
        "CodebaseRelease",
        null=True,
        related_name="latest_version",
        on_delete=models.SET_NULL,
    )

    repository_url = models.URLField(
        blank=True,
        help_text=_(
            "URL to code repository, e.g., https://github.com/comses/wolf-sheep"
        ),
    )
    replication_text = models.TextField(
        blank=True,
        help_text=_("URL / DOI / citation for the original model being replicated"),
    )
    # FIXME: original Drupal data was stored as text fields -
    # after catalog integration remove these / replace with M2M relationships to Publication entities
    # publication metadata
    references_text = models.TextField(
        blank=True,
        help_text=_("References to related publications (DOIs or citation text"),
    )
    associated_publication_text = models.TextField(
        blank=True,
        help_text=_(
            "DOI, Permanent URL, or citation to a publication associated with this codebase."
        ),
    )
    tags = ClusterTaggableManager(through=CodebaseTag)
    # evaluate this JSONField as an add-anything way to record relationships between this Codebase and other entities
    # with URLs / resolvable identifiers
    relationships = models.JSONField(default=list)

    # JSONField list of image metadata records with paths referring to self.relative_media_path()
    media = models.JSONField(
        default=list,
        help_text=_("JSON metadata dict of media associated with this Codebase"),
    )

    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="codebases", on_delete=models.PROTECT
    )

    objects = CodebaseQuerySet.as_manager()

    search_fields = [
        index.SearchField("title", boost=10.0),
        index.SearchField("description", boost=8.0),
        index.SearchField("get_all_contributors_search_fields", boost=5.0),
        index.SearchField("references_text", boost=2.0),
        index.SearchField("permanent_url"),
        index.SearchField("associated_publication_text", boost=4.0),
        index.RelatedFields(
            "tags",
            [
                index.SearchField("name"),
            ],
        ),
        # filter and sort fields
        index.FilterField("id"),
        index.FilterField("all_release_frameworks"),
        index.FilterField("all_release_programming_languages"),
        index.FilterField("is_marked_spam"),
        index.FilterField("last_modified"),
        index.FilterField("peer_reviewed"),
        index.FilterField("featured"),
        index.FilterField("is_replication"),
        index.FilterField("live"),
        index.FilterField("first_published_at"),
        index.FilterField("last_published_on"),
    ]

    HAS_PUBLISHED_KEY = True

    @property
    def is_replication(self):
        return bool(self.replication_text.strip())

    @property
    def concatenated_tags(self):
        return " ".join(self.tags.values_list("name", flat=True))

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

    def get_image_urls(self, spec="max-900x600"):
        urls = []
        for image in self.featured_images.all():
            try:
                rendition = image.get_rendition(Filter(spec=spec))
                urls.append(rendition.url)
            except Exception:
                logger.warn("Unable to find featured image %s for %s", image, self)
                pass  # image does not exist, ignore
        return urls

    def get_featured_rendition_url(self):
        featured_image = self.get_featured_image()
        if featured_image:
            return featured_image.get_rendition("max-900x600").url
        return None

    def subpath(self, *args):
        return pathlib.Path(self.base_library_dir, *args)

    @property
    def upload_path(self):
        return self.relative_media_path("uploads")

    def media_dir(self, *args):
        return pathlib.Path(settings.LIBRARY_ROOT, self.relative_media_path(*args))

    def relative_media_path(self, *args):
        return pathlib.Path(str(self.uuid), "media", *args)

    @property
    def summarized_description(self):
        if self.summary:
            return self.summary
        # FIXME: convert to cached/regenerate-able AI summary of model description
        raw_description = self.description.raw
        lines = raw_description.splitlines()
        max_lines = 6
        if len(lines) > max_lines:
            return "{0} \n...".format("\n".join(lines[:max_lines]))
        return raw_description

    @property
    def base_library_dir(self):
        # FIXME: slice up UUID eventually if needed
        return pathlib.Path(settings.LIBRARY_ROOT, str(self.uuid))

    @property
    def base_git_dir(self):
        return pathlib.Path(settings.REPOSITORY_ROOT, str(self.uuid))

    @property
    def codebase_contributors_redis_key(self):
        return f"codebase:contributors:{self.identifier}"

    @property
    def codebase_authors_redis_key(self):
        return f"codebase:authors:{self.identifier}"

    def clear_contributors_cache(self):
        cache.delete(self.codebase_contributors_redis_key)
        cache.delete(self.codebase_authors_redis_key)

    def compute_contributors(self, force=False):
        """
        caches and returns a two values: codebase_contributors and codebase_authors
        codebase_contributors are all contributors to the release
        codebase_authors are the contributors to the release that should be included in the citation
        """
        contributors_redis_key = self.codebase_contributors_redis_key
        codebase_contributors = cache.get(contributors_redis_key) if not force else None
        codebase_authors = (
            cache.get(self.codebase_authors_redis_key) if not force else None
        )

        codebase_authors_dict = OrderedDict()

        if codebase_contributors is None:
            codebase_contributors_dict = OrderedDict()
            for release_contributor in ReleaseContributor.objects.for_codebase(self):
                contributor = release_contributor.contributor
                # set to None as a makeshift OrderedSet implementation
                codebase_contributors_dict[contributor] = None
                # only include citable authors in returned codebase_authors
                if release_contributor.include_in_citation:
                    codebase_authors_dict[contributor] = None
            # PEP 448 syntax to unpack dict keys into list literal
            # https://www.python.org/dev/peps/pep-0448/
            codebase_contributors = [*codebase_contributors_dict]
            codebase_authors = [*codebase_authors_dict]
            cache.set(contributors_redis_key, codebase_contributors)
            cache.set(self.codebase_authors_redis_key, codebase_authors)
        return codebase_contributors, codebase_authors

    @property
    def all_contributors(self):
        """Get all the contributors associated with this codebase. A contributor is associated
        with a codebase if any release associated with that codebase is also associated with the
        same contributor.

        Caching contributors on _all_contributors makes it possible to ask for
        codebase_contributors in bulk"""
        if not hasattr(self, "_all_contributors"):
            all_contributors, all_authors = self.compute_contributors(force=True)
            self._all_contributors = all_contributors
            self._all_authors = all_authors
        return self._all_contributors

    @property
    def all_authors(self):
        if not hasattr(self, "_all_authors"):
            all_contributors, all_authors = self.compute_contributors(force=True)
            self._all_contributors = all_contributors
            self._all_authors = all_authors
        return self._all_authors

    @property
    def author_list(self):
        return [c.get_full_name() for c in self.all_authors if c.has_name]

    @property
    def contributor_list(self):
        return [c.get_full_name() for c in self.all_contributors if c.has_name]

    def get_all_contributors_search_fields(self):
        return " ".join(
            [c.get_aggregated_search_fields() for c in self.all_contributors]
        )

    @property
    def all_release_frameworks(self):
        return list(
            self.releases.exclude(platform_tags__isnull=True).values_list(
                "platform_tags__name", flat=True
            )
        )

    @property
    def all_release_programming_languages(self):
        return list(
            self.releases.exclude(programming_languages__isnull=True).values_list(
                "programming_languages__name", flat=True
            )
        )

    def download_count(self):
        return CodebaseReleaseDownload.objects.filter(
            release__codebase__id=self.id
        ).count()

    def ordered_releases(self, has_change_perm=False, **kwargs):
        releases = self.releases.order_by("-version_number").filter(**kwargs)
        return (
            releases
            if has_change_perm
            else releases.filter(status=CodebaseRelease.Status.PUBLISHED)
        )

    @classmethod
    def get_list_url(cls):
        return reverse("library:codebase-list")

    @staticmethod
    def format_doi_url(doi_string):
        return f"https://doi.org/{doi_string}" if doi_string else ""

    @cached_property
    def permanent_url(self):
        if self.doi:
            return self.doi_url
        return f"{settings.BASE_URL}{self.get_absolute_url()}"

    def get_absolute_url(self):
        return reverse(
            "library:codebase-detail", kwargs={"identifier": self.identifier}
        )

    def get_draft_url(self):
        return reverse(
            "library:codebaserelease-draft", kwargs={"identifier": self.identifier}
        )

    def media_url(self, name):
        return f"{self.get_absolute_url()}/media/{name}"

    @cached_property
    def doi_url(self):
        return Codebase.format_doi_url(self.doi)

    def latest_accessible_release(self, user):
        return (
            CodebaseRelease.objects.accessible(user)
            .filter(codebase=self)
            .order_by("-last_modified")
            .first()
        )

    def get_all_next_possible_version_numbers(self, minor_only=False):
        if self.releases.exists():
            possible_version_numbers = set()
            all_releases = self.releases.all()
            for release in all_releases:
                possible_version_numbers.update(
                    release.possible_next_versions(minor_only)
                )
            for release in all_releases:
                possible_version_numbers.discard(release.version_info)
            return possible_version_numbers
        else:
            return {
                SemanticVersion.DEFAULT,
            }

    def next_version_number(self, minor_only=True):
        possible_version_numbers = self.get_all_next_possible_version_numbers(
            minor_only=minor_only
        )
        next_version_number = max(possible_version_numbers)
        return str(next_version_number)

    def import_media(self, fileobj, user=None, title=None, images_only=True):
        if user is None:
            user = self.submitter

        name = os.path.basename(fileobj.name)

        if title is None:
            title = name or self.title

        path = self.media_dir(name)
        os.makedirs(str(path.parent), exist_ok=True)
        with path.open("wb") as f:
            f.write(fileobj.read())

        is_image = fs.is_image(str(path))
        if not is_image and images_only:
            logger.info("removing non image file: %s", path)
            path.unlink()
            raise UnsupportedMediaType(
                fs.mimetypes.guess_type(name)[0],
                detail=f"{name} has the wrong file type. You can only upload {settings.ACCEPTED_IMAGE_TYPES} files",
            )
        image_metadata = {
            "name": name,
            "path": str(self.media_dir()),
            "mimetype": fs.mimetypes.guess_type(str(path)),
            "url": self.media_url(name),
            "featured": is_image,
        }

        logger.info("featured image: %s", image_metadata)
        if image_metadata["featured"]:
            filename = image_metadata["name"]
            path = pathlib.Path(image_metadata["path"], filename)
            image = CodebaseImage(
                codebase=self,
                title=title,
                file=ImageFile(path.open("rb")),
                uploaded_by_user=user,
            )
            image.save()
            self.featured_images.add(image)
            logger.info("added featured image")
            return image
        else:
            self.media.append(image_metadata)
            return image_metadata

    @transaction.atomic
    def get_or_create_draft(self):
        existing_draft = self.releases.filter(
            status=CodebaseRelease.Status.DRAFT
        ).first()
        if existing_draft:
            return existing_draft

        draft_release = self.create_release()
        # reset fields that should not be copied over to a new draft
        draft_release.doi = None
        draft_release.release_notes = ""
        draft_release.output_data_url = ""
        draft_release.save()
        return draft_release

    @transaction.atomic
    def create_review_draft_from_release(self, source_release):
        # create a new "under review" release from an existing release
        # (should only be called from a publishable release)
        source_id = source_release.id
        review_draft = self.create_release(
            status=CodebaseRelease.Status.UNDER_REVIEW, source_release=source_release
        )
        fs_api = review_draft.get_fs_api()
        fs_api.copy_originals(CodebaseRelease.objects.get(id=source_id))
        return review_draft

    def create_release_from_source(self, source_release, release_metadata):
        # cache these before removing source release id to copy it over
        contributors = ReleaseContributor.objects.filter(release_id=source_release.id)
        platform_tags = source_release.platform_tags.all()
        programming_languages = source_release.programming_languages.all()
        # set source_release.id to None to create a new release
        # see https://docs.djangoproject.com/en/4.2/topics/db/queries/#copying-model-instances
        source_release.id = None
        source_release._state.adding = True
        source_release.__dict__.update(**release_metadata)
        source_release.save()
        source_release.platform_tags.add(*platform_tags)
        source_release.programming_languages.add(*programming_languages)
        contributors.copy_to(source_release)
        return source_release

    @transaction.atomic
    def create_release(
        self, initialize=True, status=None, source_release=None, **overrides
    ):
        if status is None:
            status = CodebaseRelease.Status.DRAFT
        if source_release is None:
            source_release = self.releases.last()

        existing_draft = self.releases.filter(status=status).first()
        if existing_draft:
            logger.warn(
                "Creating a new %s release when one already exists: %s",
                status,
                existing_draft.identifier,
            )
        release_metadata = dict(
            submitter=self.submitter,
            version_number=self.next_version_number(),
            identifier=None,
            status=status,
            share_uuid=uuid.uuid4(),
            first_published_at=None,
            last_published_on=None,
            doi=None,
            peer_reviewed=False,
        )

        if source_release is None:  # this is the first release of the codebase
            release_metadata["codebase"] = self
            release_metadata.update(overrides)
            release = CodebaseRelease.objects.create(**release_metadata)
            # add submitter as a release contributor automatically
            contributor, created = Contributor.from_user(self.submitter)
            release.add_contributor(contributor)
        else:
            # copy source release metadata (previous or specified source)
            release = self.create_release_from_source(source_release, release_metadata)

        if initialize:
            release.get_fs_api()  # implicitly initializes the release filesystem

        if release.is_published:
            self.latest_version = release
            self.save()
        return release

    @classmethod
    def get_indexed_objects(cls):
        return cls.objects.public()

    def __str__(self):
        return f"[codebase] {self.title} {self.date_created} (identifier:{self.identifier}, live:{self.live})"


class CodebaseImageQuerySet(ImageQuerySet):
    def accessible(self, user):
        return self.filter(uploaded_by_user=user)


class CodebaseImage(AbstractImage):
    codebase = models.ForeignKey(
        Codebase, related_name="featured_images", on_delete=models.CASCADE
    )
    file = models.ImageField(
        verbose_name=_("file"),
        upload_to=get_upload_to,
        width_field="width",
        height_field="height",
        storage=FileSystemStorage(location=settings.LIBRARY_ROOT),
    )

    admin_form_fields = Image.admin_form_fields + ("codebase", "file")

    objects = CodebaseImageQuerySet.as_manager()

    def get_upload_to(self, filename):
        # adapted from wagtailimages/models
        folder_name = str(self.codebase.relative_media_path())
        # use string_to_ascii on filename to sidestep issues with filesystem encoding
        ascii_filename = string_to_ascii(
            self.file.field.storage.get_valid_name(filename)
        )
        # Truncate filename so it fits in the 100 character limit
        # https://code.djangoproject.com/ticket/9893
        full_path = os.path.join(folder_name, ascii_filename)
        if len(full_path) >= 95:
            chars_to_trim = len(full_path) - 94
            prefix, extension = os.path.splitext(ascii_filename)
            ascii_filename = prefix[:-chars_to_trim] + extension
            full_path = os.path.join(folder_name, ascii_filename)

        logger.debug("codebase image full path: %s", full_path)
        return full_path


class CodebaseRendition(AbstractRendition):
    image = models.ForeignKey(
        CodebaseImage, related_name="renditions", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)


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
            release_contributor_qs = ReleaseContributor.objects.only(
                "id", "contributor_id", "release_id"
            )

        contributor_qs = Contributor.objects.prefetch_related("user").prefetch_related(
            "tagged_contributors__tag"
        )
        release_contributor_qs = release_contributor_qs.prefetch_related(
            Prefetch("contributor", contributor_qs)
        )

        return self.prefetch_related(
            Prefetch("codebase_contributors", release_contributor_qs)
        )

    def with_platforms(self):
        return self.prefetch_related("tagged_release_platforms__tag")

    def with_programming_languages(self):
        return self.prefetch_related("tagged_release_languages__tag")

    def with_codebase(self):
        return self.prefetch_related(
            models.Prefetch(
                "codebase", Codebase.objects.with_tags().with_featured_images()
            )
        )

    def with_submitter(self):
        return self.prefetch_related("submitter")

    def public(self, **kwargs):
        return self.filter(status=CodebaseRelease.Status.PUBLISHED, **kwargs)

    def accessible_without_codebase(self, user):
        return get_viewable_objects_for_user(user, queryset=self)

    def accessible(self, user):
        return get_viewable_objects_for_user(user, queryset=self)

    def latest_for_feed(self, number=10, include_all=False):
        qs = (
            self.public()
            .select_related("codebase", "submitter__member_profile")
            .annotate(description=models.F("codebase__description"))
            .order_by("-date_created")
        )
        if include_all:
            return qs
        return qs[:number]

    def with_cc_license(self, **kwargs):
        return self.filter(license__in=License.objects.creative_commons(), **kwargs)


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

    class Status(models.TextChoices):
        """
        Represents the various states a release can be in.
        """

        # editable and not live
        DRAFT = "draft", _("Draft")
        # equivalent to draft but indicates that a release is under review and should not
        # block the normal flow of creating/publishing new releases
        UNDER_REVIEW = "under_review", _("Under review")
        # status given after completing the review process, not editable and not live
        REVIEW_COMPLETE = "review_complete", _("Review complete")
        # not editable and live
        PUBLISHED = "published", _("Published")
        # indicates a release that was once published but has been unpublished
        UNPUBLISHED = "unpublished", _("Unpublished")

    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    status = models.CharField(
        choices=Status.choices,
        default=Status.DRAFT,
        help_text=_("The current status of this codebase release."),
        max_length=32,
    )

    first_published_at = models.DateTimeField(null=True, blank=True)
    last_published_on = models.DateTimeField(null=True, blank=True)

    peer_reviewed = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)
    share_uuid = models.UUIDField(default=None, blank=True, null=True, unique=True)
    identifier = models.CharField(max_length=128, unique=True, null=True)
    doi = models.CharField(max_length=128, unique=True, null=True)
    license = models.ForeignKey(License, null=True, on_delete=models.SET_NULL)
    release_notes = MarkdownField(
        blank=True,
        max_length=2048,
        help_text=_("Markdown formattable text, e.g., run conditions"),
    )
    summary = models.CharField(max_length=1000, blank=True)
    documentation = models.FileField(
        null=True, help_text=_("Fulltext documentation file (PDF/PDFA)")
    )
    embargo_end_date = models.DateTimeField(null=True, blank=True)
    output_data_url = models.URLField(
        blank=True, help_text=_("Permanent URL to output data from this model.")
    )
    version_number = models.CharField(
        max_length=32, help_text=_("semver string, e.g., 1.0.5, see semver.org")
    )

    os = models.CharField(max_length=32, choices=OS.choices, blank=True)
    dependencies = models.JSONField(
        default=list,
        help_text=_(
            "JSON list of software dependencies (identifier, name, version, packageSystem, OS, URL)"
        ),
    )
    """
    platform and programming language tags are also dependencies that can reference additional metadata in the
    dependencies JSONField
    """
    platform_tags = ClusterTaggableManager(
        through=CodebaseReleasePlatformTag, related_name="platform_codebase_releases"
    )
    platforms = models.ManyToManyField(Platform)
    programming_languages = ClusterTaggableManager(
        through=ProgrammingLanguage, related_name="pl_codebase_releases"
    )
    codebase = models.ForeignKey(
        Codebase, related_name="releases", on_delete=models.PROTECT
    )
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="releases", on_delete=models.PROTECT
    )
    contributors = models.ManyToManyField(Contributor, through="ReleaseContributor")
    submitted_package = models.FileField(
        upload_to=Codebase._release_upload_path,
        max_length=1000,
        null=True,
        storage=FileSystemStorage(location=settings.LIBRARY_ROOT),
    )
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
        index.SearchField("release_notes"),
        index.SearchField("summary"),
        index.SearchField("permanent_url"),
        index.SearchField("identifier"),
        index.FilterField("os"),
        index.FilterField("first_published_at"),
        index.FilterField("last_published_on"),
        index.FilterField("last_modified"),
        index.FilterField("peer_reviewed"),
        index.FilterField("flagged"),
        index.RelatedFields(
            "platform_tags",
            [
                index.SearchField("name"),
            ],
        ),
        index.RelatedFields(
            "programming_languages",
            [
                index.SearchField("name"),
            ],
        ),
        index.RelatedFields(
            "contributors",
            [
                index.SearchField("get_aggregated_search_fields"),
            ],
        ),
    ]

    HAS_PUBLISHED_KEY = True

    def regenerate_share_uuid(self):
        self.share_uuid = uuid.uuid4()
        self.save()

    def get_edit_url(self):
        return reverse(
            "library:codebaserelease-edit",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    def get_publish_url(self):
        return f"{self.get_edit_url()}?publish"

    def get_list_url(self):
        return reverse(
            "library:codebaserelease-list",
            kwargs={"identifier": self.codebase.identifier},
        )

    def get_absolute_url(self):
        return reverse(
            "library:codebaserelease-detail",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    def get_request_peer_review_url(self):
        return reverse(
            "library:codebaserelease-request-peer-review",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    def get_download_url(self):
        return reverse(
            "library:codebaserelease-download",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    def get_notify_reviewers_of_changes_url(self):
        return reverse(
            "library:codebaserelease-notify-reviewers-of-changes",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    def get_review(self):
        review = getattr(self, "review", None)
        return review if review and not review.closed else None

    def get_review_status_display(self):
        review = self.get_review()
        if review:
            return review.get_simplified_status_display()
        return "Unreviewed"

    def get_review_download_url(self):
        if not self.share_uuid:
            self.regenerate_share_uuid()
        return reverse(
            "library:codebaserelease-share-download",
            kwargs={"share_uuid": self.share_uuid},
        )

    def validate_publishable(self):
        self.validate_metadata()
        self.validate_uploaded_files()
        if self.is_under_review:
            # if under review, raise validation error if review is not complete
            review = self.get_review()
            if review and not review.is_complete:
                raise ValidationError(
                    _(
                        "Releases under review cannot be published until the review is complete."
                    )
                )

    def validate_metadata(self):
        """
        Validates that this CodebaseRelease has enough metadata to be publish()-able

        Does not validate files

        metadata: has license, author contributor, programming languages, software framework, operating system
        :return: True if this codebase release satisfies publishing metadata requirements,
        raises a ValidationError with appropriate error messages if any metadata is missing
        """
        errors = []

        # naive check for metadata being present (i.e., None or false-y values)
        if not self.license:
            errors.append(ValidationError(_("Please specify a software license.")))
        if not self.programming_languages.exists():
            errors.append(
                ValidationError(
                    _(
                        "Please list at least one programming language used to implement this model."
                    )
                )
            )
        if not self.os:
            errors.append(
                ValidationError(
                    _("Please specify compatible operating systems for this model.")
                )
            )
        if not self.contributors.exists():
            errors.append(ValidationError(_("Please add at least one contributor.")))
        if errors:
            raise ValidationError(errors)
        return True

    def validate_uploaded_files(self):
        fs_api = self.get_fs_api()
        storage = fs_api.get_stage_storage(StagingDirectories.sip)
        code_msg = self.check_files(storage, FileCategoryDirectories.code)
        docs_msg = self.check_files(storage, FileCategoryDirectories.docs)
        msg = " ".join(m for m in [code_msg, docs_msg] if m)
        if msg:
            raise ValidationError(msg)
        return True

    @staticmethod
    def check_files(storage, category: FileCategoryDirectories):
        # FIXME: document and/or refactor this API, should raise an exception or ...
        # currently returns an error message or ""
        uploaded_files = []
        if storage.exists(category.name):
            uploaded_files = list(storage.list(category))
        if uploaded_files:
            return ""
        else:
            return f"Must have at least one {category.name} file."

    @property
    def version_info(self):
        if self.version_number:
            try:
                return semver.parse_version_info(self.version_number)
            except ValueError:
                logger.exception("invalid version number: %s", self.version_number)
        return None

    @property
    def share_url(self):
        if not self.share_uuid:
            self.regenerate_share_uuid()
        return reverse(
            "library:codebaserelease-share-detail",
            kwargs={"share_uuid": self.share_uuid},
        )

    @property
    def regenerate_share_url(self):
        return reverse(
            "library:codebaserelease-regenerate-share-uuid",
            kwargs={
                "identifier": self.codebase.identifier,
                "version_number": self.version_number,
            },
        )

    @property
    def is_peer_review_requestable(self):
        """
        Returns true if this release is
        1. ready to be published
        2. has not already been peer reviewed
        3. a related PeerReview does not exist
        """
        return (
            self.is_publishable and not self.peer_reviewed and self.get_review() is None
        )

    @property
    def is_publishable(self):
        """
        Returns true if this release is ready to be published
        """
        try:
            self.validate_publishable()
            return True
        except ValidationError:
            return False

    @property
    def is_latest_version(self):
        if self.codebase.latest_version:
            return self.version_number == self.codebase.latest_version.version_number
        logger.warning("Codebase %s has no latest version", self.codebase)
        return True

    @property
    def doi_url(self):
        if self.doi:
            return Codebase.format_doi_url(self.doi)
        return self.comses_permanent_url

    @property
    def comses_permanent_url(self):
        return f"{settings.BASE_URL}{self.get_absolute_url()}"

    @property
    def permanent_url(self):
        if self.doi:
            return self.doi_url
        return self.comses_permanent_url

    @cached_property
    def citation_authors(self):
        authors = self.submitter.member_profile.name
        author_list = self.codebase.author_list
        if author_list:
            authors = ", ".join(author_list)
        else:
            logger.warning(
                "No authors found for release, using default submitter name: %s",
                self.submitter,
            )
        return authors

    @cached_property
    def citation_text(self):
        if not self.live:
            return "This model must be published in order to be citable."
        return '{authors} ({publish_date}). "{title}" (Version {version}). _{cml}_. Retrieved from: {purl}'.format(
            authors=self.citation_authors,
            publish_date=self.last_published_on.strftime("%Y, %B %d"),
            title=self.codebase.title,
            version=self.version_number,
            cml="CoMSES Computational Model Library",
            purl=self.permanent_url,
        )

    def download_count(self):
        return self.downloads.count()

    @property
    def title(self):
        return f"{self.codebase.title} v{self.version_number}"

    @property
    def archive_filename(self):
        return f"{slugify(self.codebase.title)}_v{self.version_number}.zip"

    @property
    def contributor_list(self):
        """Returns all contributors for just this CodebaseRelease"""
        return [
            c.contributor.get_full_name()
            for c in self.index_ordered_release_contributors
            if c.contributor.has_name
        ]

    @property
    def index_ordered_release_contributors(self):
        return self.codebase_contributors.select_related("contributor").order_by(
            "index"
        )

    @cached_property
    def bagit_info(self):
        return {
            "Contact-Name": self.submitter.get_full_name(),
            "Contact-Email": self.submitter.email,
            "Author": self.contributor_list,
            "Version-Number": self.version_number,
            "Codebase-DOI": str(self.codebase.doi),
            "DOI": str(self.doi),
            # FIXME: check codemeta for additional metadata
        }

    @cached_property
    def codemeta(self):
        """Returns a CodeMeta object that can be dumped to json"""
        return CodeMeta.build(self)

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def is_under_review(self):
        return self.status == self.Status.UNDER_REVIEW

    @property
    def is_review_complete(self):
        return self.status == self.Status.REVIEW_COMPLETE

    @property
    def live(self):
        return self.is_published

    @property
    def can_edit_originals(self):
        """return true if the original (unpublished) files are editable"""
        return not self.live and not self.is_review_complete

    def get_status_display(self):
        return self.Status(self.status).label

    def get_status_color(self):
        COLOR_MAP = {
            self.Status.DRAFT: "warning",
            self.Status.UNPUBLISHED: "gray",
            self.Status.UNDER_REVIEW: "danger",
            self.Status.PUBLISHED: "success",
            self.Status.REVIEW_COMPLETE: "primary",
        }
        return COLOR_MAP.get(self.status)

    @property
    def codemeta_json(self):
        return self.codemeta.to_json()

    def create_or_update_codemeta(self, force=True):
        return self.get_fs_api().create_or_update_codemeta(force=force)

    def get_fs_api(
        self, mimetype_mismatch_message_level=MessageLevels.error
    ) -> CodebaseReleaseFsApi:
        return CodebaseReleaseFsApi.initialize(
            self, mimetype_mismatch_message_level=mimetype_mismatch_message_level
        )

    def add_contributor(self, contributor: Contributor, role=Role.AUTHOR, index=None):
        # Check if a ReleaseContributor with the same contributor already exists
        existing_release_contributor = self.codebase_contributors.filter(
            contributor=contributor
        ).first()

        if existing_release_contributor is None:
            if index is None:
                index = self.codebase_contributors.all().count()
            # Create a new ReleaseContributor instance if the contributor is not already associated
            new_release_contributor = self.codebase_contributors.create(
                contributor=contributor, roles=[role], index=index
            )
            return new_release_contributor
        else:
            if role not in existing_release_contributor.roles:
                # Update the roles of the existing ReleaseContributor instance
                existing_release_contributor.roles.append(role)
                existing_release_contributor.save()

            return existing_release_contributor

    @transaction.atomic
    def publish(self):
        self.validate_publishable()
        self._publish()

    def _publish(self):
        if not self.live:
            now = timezone.now()
            self.first_published_at = now
            self.last_published_on = now
            self.status = self.Status.PUBLISHED
            self.get_fs_api().build_published_archive(force=True)
            self.save()
            codebase = self.codebase
            codebase.latest_version = self
            codebase.live = True
            codebase.last_published_on = now
            if codebase.first_published_at is None:
                codebase.first_published_at = now
            codebase.save()

    @transaction.atomic
    def unpublish(self):
        self.status = self.Status.UNPUBLISHED
        self.last_published_on = None
        self.first_published_at = None
        self.save()
        codebase = self.codebase
        # if this is the only public release, unpublish the codebase as well
        if not codebase.releases.filter(status=self.Status.PUBLISHED).exists():
            codebase.live = False
            codebase.last_published_on = None
            codebase.first_published_at = None
            codebase.save()

    def possible_next_versions(self, minor_only=False):
        return SemanticVersion.possible_next_versions(self.version_number, minor_only)

    def get_allowed_version_numbers(self):
        codebase = Codebase.objects.prefetch_related(
            Prefetch("releases", CodebaseRelease.objects.exclude(id=self.id))
        ).get(id=self.codebase_id)
        return codebase.get_all_next_possible_version_numbers()

    def set_version_number(self, version_number):
        if self.is_published:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "You cannot set the version number on a published release."
                    ]
                }
            )
        try:
            semver.parse(version_number)
        except ValueError:
            raise ValidationError(
                {
                    "version_number": [
                        f"{version_number} is not a valid semantic version string."
                    ]
                }
            )
        existing_version_numbers = (
            self.codebase.releases.exclude(id=self.id)
            .order_by("version_number")
            .values_list("version_number", flat=True)
        )
        if version_number in existing_version_numbers:
            raise ValidationError(
                {
                    "version_number": [
                        f"Another release has this version number {version_number}. Please select a different version number."
                    ]
                }
            )
        self.version_number = version_number

    @classmethod
    def get_indexed_objects(cls):
        return cls.objects.public()

    def __str__(self):
        return f"[codebase_release] {self.codebase} (submitter:{self.submitter}, v:{self.version_number})"

    class Meta:
        unique_together = ("codebase", "version_number")


class ReleaseContributorQuerySet(models.QuerySet):
    def for_codebase(self, codebase, ordered=True):
        qs = self.select_related("contributor").filter(
            release__codebase=codebase, release__status=CodebaseRelease.Status.PUBLISHED
        )
        if ordered:
            return qs.order_by("release__date_created", "index")
        return qs

    def copy_to(self, release: CodebaseRelease):
        release_contributors = list(self)
        for release_contributor in release_contributors:
            release_contributor.id = None
            release_contributor.release = release
        return self.bulk_create(release_contributors)

    def authors(self, release):
        return (
            self.select_related("contributor")
            .filter(
                release=release, include_in_citation=True, roles__contains="{author}"
            )
            .order_by("index")
        )

    def nonauthors(self, release):
        return (
            self.select_related("contributor")
            .filter(release=release, include_in_citation=True)
            .exclude(roles__contains="{author}")
            .order_by("index")
        )


class ReleaseContributor(models.Model):
    release = models.ForeignKey(
        CodebaseRelease, on_delete=models.CASCADE, related_name="codebase_contributors"
    )
    contributor = models.ForeignKey(
        Contributor, on_delete=models.CASCADE, related_name="codebase_contributors"
    )
    include_in_citation = models.BooleanField(default=True)
    roles = ArrayField(
        models.CharField(
            max_length=100,
            choices=Role.choices,
            default=Role.AUTHOR,
            help_text=_(
                "Roles from https://www.ngdc.noaa.gov/metadata/published/xsd/schema/resources/Codelist/gmxCodelists.xml#CI_RoleCode"
            ),
        ),
        default=list,
    )
    index = models.PositiveSmallIntegerField(
        help_text=_("Ordering field for codebase contributors")
    )

    objects = ReleaseContributorQuerySet.as_manager()

    def __str__(self):
        return f"[release_contributor] (release:{self.release}, contributor:{self.contributor})"


class ReviewerRecommendation(models.TextChoices):
    ACCEPT = (
        "accept",
        _("This computational model meets CoMSES Net peer review requirements."),
    )
    REVISE = (
        "revise",
        _(
            "This computational model must be revised to meet CoMSES Net peer review requirements."
        ),
    )


class ReviewStatus(models.TextChoices):
    """
    Review status represents the aggregate status of the review.

    Used by the editor, author and reviewer to determine who has to respond and if the review is complete
    """

    # No reviewer has given feedback
    AWAITING_REVIEWER_FEEDBACK = (
        "awaiting_reviewer_feedback",
        _("Awaiting reviewer feedback"),
    )
    # At least one reviewer has provided feedback on a model and an editor has not requested changes
    # to the model
    AWAITING_EDITOR_FEEDBACK = "awaiting_editor_feedback", _("Awaiting editor feedback")
    # An editor has requested changes to a model. The author has either not given changes or
    # given changes that the editor has not approved of yet or has asked further revisions on
    AWAITING_AUTHOR_CHANGES = (
        "awaiting_author_changes",
        _("Awaiting author release changes"),
    )
    # The model review process is complete
    COMPLETE = "complete", _("Review is complete")

    @classmethod
    def as_json(cls):
        return json.dumps([status.name for status in cls])

    @property
    def is_pending(self):
        return self != ReviewStatus.COMPLETE

    @property
    def simple_display_message(self):
        return "Peer review in process" if self.is_pending else "Peer reviewed"


class PeerReviewEvent(models.TextChoices):
    """
    The review event represents events that have occurred on a review.

    Used by the editor to understand the history of changes applied to the models
    """

    INVITATION_SENT = "invitation_sent", _("Reviewer has been invited")
    INVITATION_RESENT = "invitation_resent", _("Reviewer invitation has been resent")
    INVITATION_ACCEPTED = "invitation_accepted", _("Reviewer has accepted invitation")
    INVITATION_DECLINED = "invitation_declined", _("Reviewer has declined invitation")
    REVIEWER_FEEDBACK_SUBMITTED = (
        "reviewer_feedback_submitted",
        _("Reviewer has given feedback"),
    )
    AUTHOR_RESUBMITTED = (
        "author_resubmitted",
        _("Author has resubmitted release for review"),
    )
    REVIEW_STATUS_UPDATED = (
        "review_status_updated",
        _("Editor manually changed review status"),
    )
    REVISIONS_REQUESTED = (
        "revisions_requested",
        _("Editor has requested revisions to this release"),
    )
    RELEASE_CERTIFIED = (
        "release_certified",
        _(
            "Editor has taken reviewer feedback into account and certified this release as peer reviewed"
        ),
    )
    REVIEW_CLOSED = "review_closed", _("Peer review was closed")
    REVIEW_REOPENED = "review_reopened", _("Peer review was reopened")


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
        if query:
            return get_search_queryset(query, queryset)
        return queryset

    def review_open(self, **kwargs):
        return self.filter(closed=False, **kwargs)

    def requires_editor_input(self):
        return self.annotate(
            n_accepted_invites=Count(
                "invitation_set", filter=Q(invitation_set__accepted=True)
            )
        ).filter(
            Q(n_accepted_invites=0) | Q(status=ReviewStatus.AWAITING_EDITOR_FEEDBACK)
        )

    def author_changes_requested(self):
        return self.filter(status=ReviewStatus.AWAITING_AUTHOR_CHANGES)

    def reviewer_feedback_requested(self):
        return self.filter(status=ReviewStatus.AWAITING_REVIEWER_FEEDBACK)

    def with_filters(self, query_params):
        queryset = self
        if not query_params.get("include_closed"):
            queryset = queryset.review_open()
        if query_params.get("requires_editor_input"):
            queryset = queryset.requires_editor_input()
        if query_params.get("author_changes_requested"):
            queryset = queryset.author_changes_requested()
        if query_params.get("reviewer_feedback_requested"):
            queryset = queryset.reviewer_feedback_requested()
        return queryset

    def completed(self, **kwargs):
        return self.filter(status=ReviewStatus.COMPLETE, **kwargs)

    def completed_releases(self, **kwargs):
        return CodebaseRelease.objects.filter(
            id__in=self.completed(**kwargs).values("codebase_release")
        )


@register_snippet
class PeerReview(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    status = models.CharField(
        choices=ReviewStatus.choices,
        default=ReviewStatus.AWAITING_REVIEWER_FEEDBACK,
        help_text=_("The current status of this review."),
        max_length=32,
    )
    closed = models.BooleanField(default=False)
    codebase_release = models.OneToOneField(
        CodebaseRelease, related_name="review", on_delete=models.PROTECT
    )
    submitter = models.ForeignKey(
        MemberProfile, related_name="+", on_delete=models.PROTECT
    )
    slug = models.UUIDField(default=uuid.uuid4, unique=True, null=True)

    objects = PeerReviewQuerySet.as_manager()

    panels = [
        FieldPanel("status"),
    ]

    @property
    def is_open(self):
        return not self.closed

    @property
    def is_complete(self):
        return self.status == ReviewStatus.COMPLETE

    @property
    def is_awaiting_author_changes(self):
        return self.status == ReviewStatus.AWAITING_AUTHOR_CHANGES

    @property
    def is_awaiting_reviewer_feedback(self):
        return self.status == ReviewStatus.AWAITING_REVIEWER_FEEDBACK

    def get_simplified_status_display(self):
        return ReviewStatus(self.status).simple_display_message

    def get_edit_url(self):
        return reverse("library:profile-edit", kwargs={"user_pk": self.user.id})

    def get_change_closed_url(self):
        return reverse("library:peer-review-change-closed", kwargs={"slug": self.slug})

    def get_invite(self, member_profile):
        return self.invitation_set.filter(candidate_reviewer=member_profile).first()

    @transaction.atomic
    def get_absolute_url(self):
        if not self.slug:
            self.slug = uuid.uuid4()
            self.save()
        return reverse("library:peer-review-detail", kwargs={"slug": self.slug})

    def get_event_list_url(self):
        return reverse("library:peer-review-event-list", kwargs={"slug": self.slug})

    @transaction.atomic
    def set_complete_status(self, editor: MemberProfile):
        self.status = ReviewStatus.COMPLETE
        self.save()
        self.log(
            author=editor,
            action=PeerReviewEvent.RELEASE_CERTIFIED,
            message="Model has been certified as peer reviewed",
        )
        # dont un-publish releases with a review started before the new review process
        if self.codebase_release.is_under_review:
            self.codebase_release.status = CodebaseRelease.Status.REVIEW_COMPLETE
        self.codebase_release.peer_reviewed = True
        self.codebase_release.save()
        self.codebase_release.codebase.peer_reviewed = True
        self.codebase_release.codebase.save()
        self.send_model_certified_email()

    def log(self, message: str, action: PeerReviewEvent, author: MemberProfile):
        return self.event_set.create(message=message, action=action.name, author=author)

    def editor_change_review_status(self, editor: MemberProfile, status: ReviewStatus):
        self.log(
            author=editor,
            action=PeerReviewEvent.REVIEW_STATUS_UPDATED,
            message=f"Editor changed peer review status: {self.status} -> {status}",
        )
        self.status = status
        self.save()

    def author_resubmitted_changes(self, changes_made=None):
        author = self.submitter
        self.log(
            message=f"Release has been resubmitted for review: {changes_made}",
            action=PeerReviewEvent.AUTHOR_RESUBMITTED,
            author=author,
        )
        self.send_author_updated_content_email()

    def close(self, submitter_or_editor: MemberProfile):
        if self.closed:
            return

        self.closed = True
        self.log(
            message=f"Peer review closed by {'submitter' if submitter_or_editor == self.submitter else 'editor'}",
            action=PeerReviewEvent.REVIEW_CLOSED,
            author=submitter_or_editor,
        )
        self.save()
        # do we want to send an email when a review is closed?

    def reopen(self, submitter_or_editor: MemberProfile):
        if not self.closed:
            return

        self.closed = False
        self.log(
            message=f"Peer review re-opened by {'submitter' if submitter_or_editor == self.submitter else 'editor'}",
            action=PeerReviewEvent.REVIEW_REOPENED,
            author=submitter_or_editor,
        )
        self.save()

    def send_author_updated_content_email(self):
        qs = self.invitation_set.filter(accepted=True)
        # if there are no currently accepted invitations, status should be set to awaiting editor feedback
        self.status = (
            ReviewStatus.AWAITING_REVIEWER_FEEDBACK
            if qs.exists()
            else ReviewStatus.AWAITING_EDITOR_FEEDBACK
        )
        for invitation in qs:
            invitation.send_author_resubmitted_email()
        self.save()

    def send_author_requested_peer_review_email(self):
        send_markdown_email(
            subject="Peer review: New request",
            template_name="library/review/email/review_requested.jinja",
            context={"review": self},
            to=[settings.REVIEW_EDITOR_EMAIL],
        )

    def send_model_certified_email(self):
        send_markdown_email(
            subject="Peer review completed",
            template_name="library/review/email/model_certified.jinja",
            context={"review": self},
            to=[self.submitter.email],
            cc=[settings.REVIEW_EDITOR_EMAIL],
        )

    @cached_property
    def review_status_json(self):
        return json.dumps(
            [
                {"value": choice[0], "label": str(choice[1])}
                for choice in ReviewStatus.choices
            ]
        )

    @property
    def title(self):
        return self.codebase_release.title

    @property
    def contact_author_name(self):
        return self.codebase_release.submitter.member_profile.name

    @classmethod
    def get_codebase_latest_active_review(cls, codebase):
        """returns the latest review for a codebase that is not complete and not closed"""
        qs = cls.objects.filter(codebase_release__codebase=codebase).exclude(
            Q(status=ReviewStatus.COMPLETE) | Q(closed=True)
        )
        return qs.latest("date_created") if qs.exists() else None

    def __str__(self):
        return f"[peer review] {self.title} (status: {self.status}, created: {self.date_created}, last_modified {self.last_modified})"


class PeerReviewInvitationQuerySet(models.QuerySet):
    def accepted(self, **kwargs):
        return self.filter(accepted=True, **kwargs)

    def declined(self, **kwargs):
        return self.filter(accepted=False, **kwargs)

    def pending(self, **kwargs):
        return self.filter(accepted__isnull=True, **kwargs)

    def candidate_reviewers(self, **kwargs):
        # FIXME: fairly horribly inefficient
        return MemberProfile.objects.filter(
            id__in=self.values_list("candidate_reviewer", flat=True)
        )

    def with_reviewer_statistics(self):
        return self.prefetch_related(
            models.Prefetch(
                "candidate_reviewer", PeerReview.objects.find_candidate_reviewers()
            )
        )


@register_snippet
class PeerReviewInvitation(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_sent = models.DateTimeField(default=timezone.now)
    review = models.ForeignKey(
        PeerReview, related_name="invitation_set", on_delete=models.CASCADE
    )
    editor = models.ForeignKey(
        MemberProfile, related_name="+", on_delete=models.PROTECT
    )
    candidate_reviewer = models.ForeignKey(
        MemberProfile,
        related_name="peer_review_invitation_set",
        on_delete=models.CASCADE,
    )
    optional_message = MarkdownField(
        help_text=_("Optional markdown text to be added to the email")
    )
    slug = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    accepted = models.BooleanField(
        null=True,
        verbose_name=_("Invitation status"),
        choices=(
            (None, _("Waiting for response")),
            (False, _("Decline")),
            (True, _("Accept")),
        ),
        help_text=_("Accept or decline this peer review invitation"),
    )

    objects = PeerReviewInvitationQuerySet.as_manager()

    @property
    def latest_feedback(self):
        if not self.feedback_set.exists():
            return self.feedback_set.create()
        return self.feedback_set.last()

    @property
    def expiration_date(self):
        return self.date_sent + timedelta(
            days=settings.PEER_REVIEW_INVITATION_EXPIRATION
        )

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
            logger.error(
                "Trying to send an author resubmitted notification to an unaccepted invitation - ignoring."
            )
            return
        send_markdown_email(
            subject=f"Peer review: updates to release {self.review.title}",
            template_name="library/review/email/author_updated_content_for_reviewer_email.jinja",
            context={
                "invitation": self,
                # create a fresh feedback object for the reviewer to edit
                "feedback": self.feedback_set.create(),
            },
            to=[self.reviewer_email],
            cc=[settings.REVIEW_EDITOR_EMAIL],
        )

    @transaction.atomic
    def send_candidate_reviewer_email(self, resend=False):
        self.date_sent = timezone.now()
        self.save(update_fields=["date_sent"])
        send_markdown_email(
            subject="Peer review: request to review a computational model",
            template_name="library/review/email/review_invitation.jinja",
            context={"invitation": self},
            to=[self.reviewer_email],
            cc=[settings.REVIEW_EDITOR_EMAIL],
        )
        self.review.log(
            action=(
                PeerReviewEvent.INVITATION_RESENT
                if resend
                else PeerReviewEvent.INVITATION_SENT
            ),
            author=self.editor,
            message=f"{self.editor} sent an invitation to candidate reviewer {self.candidate_reviewer}",
        )

    @transaction.atomic
    def accept(self):
        self.accepted = True
        self.save()
        feedback = self.latest_feedback
        self.review.log(
            action=PeerReviewEvent.INVITATION_ACCEPTED,
            author=self.candidate_reviewer,
            message=f"Invitation accepted by {self.candidate_reviewer}",
        )
        send_markdown_email(
            subject="Peer review: accepted invitation to review model",
            template_name="library/review/email/review_invitation_accepted.jinja",
            context={"invitation": self, "feedback": feedback},
            to=[self.reviewer_email],
            cc=[settings.REVIEW_EDITOR_EMAIL],
        )
        return feedback

    @transaction.atomic
    def decline(self):
        self.accepted = False
        self.save()
        self.review.log(
            action=PeerReviewEvent.INVITATION_DECLINED,
            author=self.candidate_reviewer,
            message=f"Invitation declined by {self.candidate_reviewer}",
        )
        send_markdown_email(
            subject="Peer review: declined invitation to review model",
            template_name="library/review/email/review_invitation_declined.jinja",
            context={"invitation": self},
            to=[settings.REVIEW_EDITOR_EMAIL],
        )

    def get_absolute_url(self):
        return reverse("library:peer-review-invitation", kwargs=dict(slug=self.slug))

    class Meta:
        unique_together = (("review", "candidate_reviewer"),)


@register_snippet
class PeerReviewerFeedback(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    invitation = models.ForeignKey(
        PeerReviewInvitation, related_name="feedback_set", on_delete=models.CASCADE
    )
    recommendation = models.CharField(
        choices=ReviewerRecommendation.choices, max_length=16, blank=True
    )
    private_reviewer_notes = MarkdownField(
        help_text=_(
            "Private reviewer notes to be sent to and viewed by the CoMSES review editors only."
        ),
        blank=True,
    )
    private_editor_notes = MarkdownField(
        help_text=_("Private editor notes regarding this peer review"), blank=True
    )
    notes_to_author = MarkdownField(
        help_text=_(
            "Editor's notes to be sent to the model author, manually compiled from other reviewer comments."
        ),
        blank=True,
    )
    has_narrative_documentation = models.BooleanField(
        default=False,
        help_text=_(
            "Is there sufficiently detailed accompanying narrative documentation? (A checked box indicates that the model has narrative documentation)"
        ),
    )
    narrative_documentation_comments = models.TextField(
        help_text=_("Reviewer comments on the narrative documentation"), blank=True
    )
    has_clean_code = models.BooleanField(
        default=False,
        help_text=_(
            "Is the code clean, well-written, and well-commented with consistent formatting? (A checked box indicates that the model code is clean)"
        ),
    )
    clean_code_comments = models.TextField(
        help_text=_("Reviewer comments on code cleanliness"), blank=True
    )
    is_runnable = models.BooleanField(
        default=False,
        help_text=_(
            "Were you able to run the model with the provided instructions? (A checked box indicates that the model is runnable)"
        ),
    )
    runnable_comments = models.TextField(
        help_text=_(
            "Reviewer comments on running the model with the provided instructions"
        ),
        blank=True,
    )
    reviewer_submitted = models.BooleanField(
        help_text=_(
            "Internal field, set to True when the reviewer has finalized their feedback and is ready for an editor to check their submission."
        ),
        default=False,
    )

    def get_absolute_url(self):
        return reverse(
            "library:peer-review-feedback-edit",
            kwargs={"slug": self.invitation.slug, "feedback_id": self.id},
        )

    def get_editor_url(self):
        return reverse(
            "library:peer-review-feedback-editor-edit",
            kwargs={"slug": self.invitation.slug, "feedback_id": self.id},
        )

    @transaction.atomic
    def reviewer_completed(self):
        """Add a reviewer gave feedback event to the log

        Preconditions:

        reviewer updated feedback
        """
        review = self.invitation.review
        review.status = ReviewStatus.AWAITING_EDITOR_FEEDBACK
        review.save()
        reviewer = self.invitation.candidate_reviewer
        review.log(
            action=PeerReviewEvent.REVIEWER_FEEDBACK_SUBMITTED,
            author=reviewer,
            message=f"Reviewer {reviewer} provided feedback",
        )
        send_markdown_email(
            subject="[CoMSES Peer Review]: reviewer feedback submitted, editor action needed",
            template_name="library/review/email/reviewer_submitted.jinja",
            context={"review": review, "invitation": self.invitation},
            to=[settings.REVIEW_EDITOR_EMAIL],
        )
        send_markdown_email(
            subject="Peer review: feedback submitted",
            template_name="library/review/email/reviewer_submitted_thanks.jinja",
            context={"review": review, "invitation": self.invitation},
            to=[reviewer.email],
            bcc=[settings.REVIEW_EDITOR_EMAIL],
        )

    @transaction.atomic
    def editor_called_for_revisions(self, editor: MemberProfile):
        """Add an editor called for revisions event to the log

        Preconditions:

        editor updated feedback
        """
        review = self.invitation.review
        review.log(
            action=PeerReviewEvent.REVISIONS_REQUESTED,
            author=editor,
            message=f"Editor {editor} called for revisions",
        )
        review.status = ReviewStatus.AWAITING_AUTHOR_CHANGES
        review.save()
        recipients = {review.submitter.email, review.codebase_release.submitter.email}
        send_markdown_email(
            subject="Peer review: revisions requested",
            template_name="library/review/email/model_revisions_requested.jinja",
            context={"review": review, "feedback": self},
            to=recipients,
            bcc=[settings.REVIEW_EDITOR_EMAIL],
        )

    def __str__(self):
        invitation = self.invitation
        return f"[peer review] {invitation.candidate_reviewer} submitted? {self.reviewer_submitted}, recommendation: {self.get_recommendation_display()}"


class CodeMeta:
    DATE_PUBLISHED_FORMAT = "%Y-%m-%d"
    COMSES_ORGANIZATION = {
        "@id": "https://ror.org/015bsfc29",
        "@type": "Organization",
        "name": "CoMSES Net",
        "url": "https://www.comses.net",
    }
    INITIAL_DATA = {
        "@context": "http://schema.org",
        "@type": "SoftwareSourceCode",
        "isPartOf": {
            "@type": "WebApplication",
            "applicationCategory": "Computational Modeling Software Repository",
            "operatingSystem": "Any",
            "name": "CoMSES Model Library",
            "url": "https://www.comses.net/codebases",
        },
        "publisher": COMSES_ORGANIZATION,
        "provider": COMSES_ORGANIZATION,
    }

    def __init__(self, metadata: dict):
        if not metadata:
            raise ValueError(
                "Initialize with a base dictionary with codemeta terms mapped to JSON-serializable values"
            )
        self.metadata = metadata

    @classmethod
    def convert_target_product(cls, codebase_release: CodebaseRelease):
        target_product = {
            "@type": "SoftwareApplication",
            "name": codebase_release.title,
            "operatingSystem": codebase_release.os,
            "applicationCategory": "Computational Model",
        }
        if codebase_release.live:
            target_product.update(
                downloadUrl=f"{settings.BASE_URL}{codebase_release.get_download_url()}",
                releaseNotes=codebase_release.release_notes.raw,
                softwareVersion=codebase_release.version_number,
                identifier=codebase_release.permanent_url,
                sameAs=codebase_release.comses_permanent_url,
            )
        image_urls = codebase_release.codebase.get_image_urls()
        if image_urls:
            target_product.update(screenshot=f"{settings.BASE_URL}{image_urls[0]}")
        return target_product

    @classmethod
    def convert_keywords(cls, codebase_release: CodebaseRelease):
        return [tag.name for tag in codebase_release.codebase.tags.all()]

    @classmethod
    def convert_platforms(cls, codebase_release: CodebaseRelease):
        return [tag.name for tag in codebase_release.platform_tags.all()]

    @classmethod
    def convert_authors(cls, codebase_release: CodebaseRelease):
        return [
            author.contributor.to_codemeta()
            for author in ReleaseContributor.objects.authors(codebase_release)
        ]

    @classmethod
    def convert_programming_languages(cls, codebase_release: CodebaseRelease):
        return [
            {"@type": "ComputerLanguage", "name": pl.name}
            for pl in codebase_release.programming_languages.all()
        ]

    @classmethod
    def build(cls, release: CodebaseRelease):
        metadata = cls.INITIAL_DATA.copy()
        codebase = release.codebase
        metadata.update(
            name=codebase.title,
            abstract=codebase.summary,
            description=codebase.description.raw,
            version=release.version_number,
            targetProduct=cls.convert_target_product(release),
            programmingLanguage=cls.convert_programming_languages(release),
            author=cls.convert_authors(release),
            identifier=release.permanent_url,
            dateCreated=release.date_created.isoformat(),
            dateModified=release.last_modified.isoformat(),
            keywords=cls.convert_keywords(release),
            runtimePlatform=cls.convert_platforms(release),
            url=release.permanent_url,
            citation=[],
        )
        if release.live:
            metadata.update(
                datePublished=release.last_published_on.strftime(
                    cls.DATE_PUBLISHED_FORMAT
                )
            )
            metadata.update(copyrightYear=release.last_published_on.year)
        if release.license:
            metadata.update(license=release.license.url)
        if codebase.repository_url:
            metadata.update(codeRepository=codebase.repository_url)
        cls.add_citation_text(metadata, codebase.references_text)
        cls.add_citation_text(metadata, codebase.replication_text)
        cls.add_citation_text(metadata, codebase.associated_publication_text)

        if release.release_notes:
            metadata.update(releaseNotes=release.release_notes.raw)
        metadata["@id"] = release.permanent_url
        return CodeMeta(metadata)

    @classmethod
    def add_citation_text(cls, metadata, text):
        if text:
            metadata.get("citation").append(cls.to_creative_work(text))

    @classmethod
    def to_creative_work(cls, text):
        return {"@type": "CreativeWork", "text": text}

    def to_json(self):
        """Returns a JSON string of this codemeta data"""
        # FIXME: should ideally validate metadata as well
        return json.dumps(self.metadata)

    def to_dict(self):
        return self.metadata.copy()


@register_snippet
class PeerReviewEventLog(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    review = models.ForeignKey(
        PeerReview, related_name="event_set", on_delete=models.CASCADE
    )
    action = models.CharField(
        choices=PeerReviewEvent.choices,
        help_text=_("status action requested."),
        max_length=32,
    )
    author = models.ForeignKey(
        MemberProfile,
        related_name="+",
        on_delete=models.CASCADE,
        help_text=_("User originating this action"),
    )
    message = models.CharField(blank=True, max_length=500)

    def add_message(self, message):
        if self.message:
            self.message += f"\n\n{message}"
        else:
            self.message = message
