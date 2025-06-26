from datetime import date
from typing import Literal
from codemeticulous.codemeta.models import (
    CodeMeta,
    Person,
    Organization,
    Role,
)
from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.datacite.models import DataCite
from codemeticulous import convert

from django.conf import settings

import logging

logger = logging.getLogger(__name__)


class CodeMetaConverter:
    """Create codemeta objects that represent the metadata for a codebase or release."""

    COMSES_ORGANIZATION = {
        "@id": "https://ror.org/015bsfc29",
        "@type": "Organization",
        "name": "CoMSES Net",
        "url": "https://www.comses.net",
    }

    COMSES_MODEL_LIBRARY_CREATIVE_WORK = {
        "@type": "WebApplication",
        "applicationCategory": "Computational Modeling Software Repository",
        "operatingSystem": "Any",
        "name": "CoMSES Model Library",
        "url": "https://www.comses.net/codebases",
    }

    @classmethod
    def convert_affiliation(cls, affiliation: dict) -> Organization:
        return Organization(
            id_=affiliation.get("ror_id") or None,
            name=affiliation.get("name"),
            url=affiliation.get("url"),
            identifier=affiliation.get("ror_id") or None,
        )

    @classmethod
    def _convert_actor(
        cls, contributor, actor_type: Literal["author", "contributor"], index: int
    ) -> Person | Organization:
        # fallback to a blank node: https://www.w3.org/TR/json-ld11/#identifying-blank-nodes
        actor_id = (
            contributor.orcid_url
            or contributor.member_profile_url(include_base_url=True)
            or f"_:{actor_type}_{index + 1}"
        )
        if contributor.is_organization:
            return Organization(
                id_=actor_id,
                name=contributor.name,
            )
        elif contributor.is_person:
            affiliation = (
                cls.convert_affiliation(contributor.primary_affiliation)
                if contributor.primary_affiliation
                else None
            )
            return Person(
                id_=actor_id,
                givenName=contributor.get_given_name() or None,
                familyName=contributor.get_family_name() or None,
                affiliation=affiliation,
                email=contributor.email or None,
            )
        else:
            raise ValueError(f"Invalid actor type '{actor_type}'")

    @classmethod
    def _convert_roles(cls, actor_id: str, roles: list[str]) -> list[Role]:
        return [
            Role(
                id_=actor_id,
                roleName=role,
            )
            for role in roles
            if role != "author"
        ]

    @classmethod
    def convert_contributors(
        cls,
        contributors,
        actor_type: Literal["author", "contributor"],
    ) -> list[Person | Organization | Role]:
        """converts a list of Contributor or ReleaseContributor objects to a list of codemeta actors.
        If ReleaseContributors are given, the roles are also converted to codemeta/schema.org roles
        """
        codemeta_actors = []
        codemeta_roles = []
        for index, contributor_or_rc in enumerate(contributors):
            contributor = (
                contributor_or_rc.contributor
                if hasattr(contributor_or_rc, "contributor")
                else contributor_or_rc
            )
            actor = cls._convert_actor(contributor, actor_type, index)
            codemeta_actors.append(actor)
            if hasattr(contributor_or_rc, "roles"):
                codemeta_roles.extend(
                    cls._convert_roles(actor.id_, contributor_or_rc.roles)
                )
        return codemeta_actors + codemeta_roles

    @classmethod
    def to_textual_creative_work(cls, text: str) -> dict:
        return {
            "@type": "CreativeWork",
            "text": text,
        }

    @classmethod
    def license_to_creative_work(cls, license) -> dict:
        creative_work_license = {
            "@type": "CreativeWork",
            "name": license.name,
        }
        if license.url:
            creative_work_license["url"] = license.url
        return creative_work_license

    @classmethod
    def url_to_datafeed(cls, url: str) -> dict:
        return {
            "@type": "DataFeed",
            "url": url,
        }

    @classmethod
    def _common_codebase_fields(cls, codebase) -> dict:
        return dict(
            type_="SoftwareSourceCode",
            name=codebase.title,
            codeRepository=(
                codebase.git_mirror.remotes.first().url
                # FIXME: coderepository can be one url, how do we determine priority?
                if codebase.git_mirror and codebase.git_mirror.remotes.first()
                else codebase.repository_url
            )
            or None,
            applicationCategory="Computational Model",
            citation=[
                cls.to_textual_creative_work(text)
                for text in [
                    codebase.references_text,
                    codebase.replication_text,
                ]
                if text
            ]
            or None,
            # tags are sorted so that comparisons are deterministic
            keywords=[tag.name for tag in codebase.tags.all().order_by("name")] or None,
            publisher=cls.COMSES_ORGANIZATION,
            description=codebase.description.raw,
            referencePublication=codebase.associated_publication_text or None,
        )

    @classmethod
    def _convert_codebase(cls, codebase) -> CodeMeta:
        return CodeMeta(
            **cls._common_codebase_fields(codebase),
            id_=codebase.permanent_url,
            identifier=(
                [codebase.doi, codebase.permanent_url]
                if codebase.doi
                else codebase.permanent_url
            ),
            author=cls.convert_contributors(codebase.all_author_contributors, "author")
            or None,
            contributor=cls.convert_contributors(
                codebase.all_nonauthor_contributors, "contributor"
            )
            or None,
            dateCreated=codebase.date_created.date() if codebase.date_created else None,
            datePublished=(
                codebase.last_published_on.date()
                if codebase.last_published_on
                else None
            ),
            url=codebase.permanent_url,
        )

    @classmethod
    def _convert_release(cls, release) -> CodeMeta:
        codebase = release.codebase
        return CodeMeta(
            **cls._common_codebase_fields(codebase),
            id_=release.permanent_url,
            identifier=(
                [release.doi, release.permanent_url]
                if release.doi
                else release.permanent_url
            ),
            programmingLanguage=[
                # FIXME: this can include "version" when langs are refactored
                {"@type": "ComputerLanguage", "name": pl.name}
                for pl in release.programming_languages.all().order_by("name")
            ],
            runtimePlatform=[
                tag.name for tag in release.platform_tags.all().order_by("name")
            ]
            or None,
            # FIXME: anything to use this for? it can be either the target os or target
            # framework (e.g. Mesa, NetLogo) but these are both already covered
            # targetProduct=release.os,
            downloadUrl=f"{settings.BASE_URL}{release.get_download_url()}",
            operatingSystem=release.os,
            releaseNotes=release.release_notes.raw,
            supportingData=(
                cls.url_to_datafeed(release.output_data_url)
                if release.output_data_url
                else None
            ),
            # FIXME: need better guidance on author vs contributor fields in CodeMeta
            author=cls.convert_contributors(
                release.author_release_contributors, "author"
            )
            or None,
            contributor=cls.convert_contributors(
                release.nonauthor_release_contributors, "contributor"
            )
            or None,
            copyrightYear=(
                release.last_published_on.year if release.last_published_on else None
            ),
            dateCreated=release.date_created.date() if release.date_created else None,
            dateModified=(
                release.last_modified.date() if release.last_modified else None
            ),
            datePublished=(
                release.last_published_on.date() if release.last_published_on else None
            ),
            license=(
                cls.license_to_creative_work(release.license)
                if release.license
                else None
            ),
            version=release.version_number,
            url=release.permanent_url,
            embargoEndDate=release.embargo_end_date,
        )

    @classmethod
    def _convert_codebase_minimal(cls, codebase) -> CodeMeta:
        return CodeMeta(
            type_="SoftwareSourceCode",
            name=codebase.title,
        )

    @classmethod
    def convert_release(cls, release) -> CodeMeta:
        try:
            return cls._convert_release(release)
        except Exception as e:
            # in case something goes horribly wrong, log the error and return a valid but
            # minimal codemeta object
            logger.exception(
                f"Error when generating codemeta for release {release}: {e}"
            )
            return cls._convert_codebase_minimal(release.codebase)

    @classmethod
    def convert_codebase(cls, codebase) -> CodeMeta:
        try:
            return cls._convert_codebase(codebase)
        except Exception as e:
            logger.exception(
                f"Error when generating codemeta for codebase {codebase}: {e}"
            )
            return cls._convert_codebase_minimal(codebase)


class CitationFileFormatConverter:
    """Create citation file format objects that represent the metadata for a codebase or release."""

    @classmethod
    def convert_release(
        cls, release, codemeta: CodeMeta | dict = None
    ) -> CitationFileFormat:
        codemeta = coerce_codemeta(codemeta, release=release)
        return convert("codemeta", "cff", codemeta)


class DataCiteConverter:
    """Create datacite metadata objects that represent the metadata for a codebase or release."""

    @classmethod
    def get_formats(cls):
        return ["text/plain"]

    @classmethod
    def to_related_identifier(
        cls, related_identifier: str, relation_type: str, related_identifier_type="DOI"
    ):
        return {
            "relatedIdentifier": related_identifier,
            "relatedIdentifierType": related_identifier_type,
            "relationType": relation_type,
        }

    @classmethod
    def get_release_related_identifiers(cls, release):
        related_identifiers = []
        if release.codebase.doi:
            related_identifiers.append(
                cls.to_related_identifier(release.codebase.doi, "IsVersionOf")
            )
        previous_release = release.get_previous_release()
        next_release = release.get_next_release()
        # set relationship to previous_release
        if previous_release and previous_release.doi:
            related_identifiers.append(
                cls.to_related_identifier(previous_release.doi, "IsNewVersionOf")
            )

        # set relationship to next_release
        if next_release and next_release.doi:
            related_identifiers.append(
                cls.to_related_identifier(next_release.doi, "IsPreviousVersionOf")
            )
        return related_identifiers or None

    @classmethod
    def get_codebase_related_identifiers(cls, codebase):
        # other identifiers to consider? (too many, prioritize which ones)
        # IsReviewedBy, IsRequiredBy, IsDocumentedBy, IsReferencedBy, IsVariantOf, IsDerivedFrom, Obsoletes, IsObsoletedBy, IsCitedBy, IsSupplementTo, IsSupplementedBy
        return [
            cls.to_related_identifier(release.doi, "HasVersion")
            for release in codebase.ordered_releases_list()
            if release.doi
        ] or None

    @classmethod
    def get_codebase_descriptions(cls, codebase):
        return [
            {
                "description": codebase.description.raw,
                "descriptionType": "Abstract",
            },
            {
                "description": "The DOI pointing to this resource is a `concept version` representing all versions of this computational model and will always redirect to the latest version of this computational model. See https://zenodo.org/help/versioning for more details on the rationale behind a concept version DOI that rolls up all versions of a given computational model or any other digital research object.",
                "descriptionType": "Other",
            },
        ]

    @classmethod
    def convert_release(cls, release, codemeta: CodeMeta | dict = None) -> DataCite:
        codemeta = coerce_codemeta(codemeta, release=release)
        # datacite always needs a publication date
        if not codemeta.datePublished:
            codemeta.datePublished = date.today()
        return convert(
            "codemeta",
            "datacite",
            codemeta,
            formats=cls.get_formats(),
            relatedIdentifiers=cls.get_release_related_identifiers(release),
        )

    @classmethod
    def convert_codebase(cls, codebase, codemeta: CodeMeta | dict = None) -> DataCite:
        codemeta = coerce_codemeta(codemeta, codebase=codebase)
        # datacite always needs a publication date
        if not codemeta.datePublished:
            codemeta.datePublished = date.today()
        return convert(
            "codemeta",
            "datacite",
            codemeta,
            # any additional fields that cannot be derived from codemeta
            descriptions=cls.get_codebase_descriptions(codebase),
            relatedIdentifiers=cls.get_codebase_related_identifiers(codebase),
        )


class ReleaseMetadataConverter:
    """Extract CoMSES CodebaseRelease metadata from various sources."""

    def __init__(
        self,
        codemeta: CodeMeta | dict | None = None,
        cff: CitationFileFormat | dict | None = None,
        github_repository: dict | None = None,
        github_release: dict | None = None,
    ) -> dict:
        self.codemeta = coerce_codemeta(codemeta)
        self.cff = coerce_cff(cff)
        self.github_repository = github_repository
        self.github_release = github_release

    def _get_field(self, source, key: str):
        """helper to retrieve a field from either a dict or object, returning
        None if the source either doesn't exist or doesn't contain the field"""
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key, None)
        return getattr(source, key, None)

    def _ensure_list(self, value):
        """return a list containing the value if it is not a list,
        or the value if it is already a list"""
        if isinstance(value, list):
            return value
        elif value is None:
            return []
        return [value]

    def extract_license_spdx_id(self) -> str | None:
        # priority: github_repository.license.spdx_id > cff.license
        gh_license = self._get_field(self.github_repository, "license")
        if isinstance(gh_license, dict):
            spdx_id = gh_license.get("spdx_id", None)
            if spdx_id:
                return spdx_id
        # cff.license should be an Enum with a valid spdx id (or a list of them)
        cff_licenses = self._ensure_list(self._get_field(self.cff, "license"))
        for cff_license in cff_licenses:
            if cff_license and cff_license.value:
                return cff_license.value

    def extract_release_notes(self) -> str | None:
        # priority: codemeta.releaseNotes > github_release.body
        # codemeta.releaseNotes can be a list, make sure its a str, take the first one
        release_notes = self._get_field(self.codemeta, "releaseNotes")
        if release_notes:
            if isinstance(release_notes, list):
                release_notes = release_notes[0]
                return release_notes if isinstance(release_notes, str) else None
            elif isinstance(release_notes, str):
                return release_notes
        body = self._get_field(self.github_release, "body")
        return body if isinstance(body, str) else None

    def extract_os(self) -> str:
        # priority: codemeta.operatingSystem
        codemeta_os = self._get_field(self.codemeta, "operatingSystem")
        if not codemeta_os:
            return ""
        if isinstance(codemeta_os, list):
            os_str = codemeta_os[0]
        elif isinstance(codemeta_os, str):
            os_str = codemeta_os
        else:
            return ""
        if os_str:
            normalized = os_str.lower()
            # attempt to match the given os string to a known platform
            if "linux" in normalized:
                return "linux"
            elif "mac" in normalized or "os x" in normalized:
                return "macos"
            elif "windows" in normalized:
                return "windows"
            elif "independent" in normalized or "any" in normalized:
                return "platform_independent"
            else:
                return "other"
        return ""

    def extract_programming_languages(self) -> list[str] | None:
        # priority: codemeta.programmingLanguage > [github_repository.language]
        codemeta_langs = self._ensure_list(
            self._get_field(self.codemeta, "programmingLanguage")
        )
        langs = []
        for codemeta_lang in codemeta_langs:
            if isinstance(codemeta_lang, str):
                langs.append(codemeta_lang)
            else:  # try to get the name from a ComputerLanguage object
                lang_name = self._get_field(codemeta_lang, "name")
                if lang_name:
                    langs.append(lang_name)
        if langs:
            return langs
        else:
            gh_lang = self._get_field(self.github_repository, "language")
            if gh_lang and isinstance(gh_lang, str):
                return [gh_lang]

    def extract_platforms(self) -> list[str] | None:
        # priority: codemeta.runtimePlatform
        runtime_platforms = self._ensure_list(
            self._get_field(self.codemeta, "runtimePlatform")
        )
        platforms = []
        for runtime_platform in runtime_platforms:
            if isinstance(runtime_platform, str):
                platforms.append(runtime_platform)
        return platforms if platforms else None

    def convert(self) -> dict:
        """return a dictionary with the metadata fields for a codebase release from
        given sources"""
        return {
            "license_spdx_id": self.extract_license_spdx_id(),
            "release_notes": self.extract_release_notes(),
            "os": self.extract_os(),
            "programming_languages": self.extract_programming_languages(),
            "platforms": self.extract_platforms(),
        }


def coerce_codemeta(
    codemeta: dict | CodeMeta | None, codebase=None, release=None
) -> CodeMeta | None:
    """
    Ensure the returned value is a CodeMeta object or None.
    - if given a CodeMeta instance, return it
    - if given a dictionary, parse it into a CodeMeta object
    - if given None, attempt to generate codemeta from the given codebase or release
    - return None if the input cannot be converted or generated
    """
    if isinstance(codemeta, CodeMeta):
        return codemeta
    if isinstance(codemeta, dict):
        try:
            return CodeMeta(**codemeta)
        except Exception:
            return None
    if codemeta is None:
        if codebase:
            return CodeMetaConverter.convert_codebase(codebase)
        elif release:
            return CodeMetaConverter.convert_release(release)
    return None


def coerce_cff(
    cff: dict | CitationFileFormat | None, release=None
) -> CitationFileFormat | None:
    """
    Ensure the returned value is a CitationFileFormat object or None.
    - if given a CitationFileFormat instance, return it
    - if given a dictionary, parse it into a CitationFileFormat object
    - if given None, attempt to generate cff from the given release
    - return None if the input cannot be converted or generated
    """
    if isinstance(cff, CitationFileFormat):
        return cff
    if isinstance(cff, dict):
        try:
            return CitationFileFormat(**cff)
        except Exception:
            return None
    if cff is None:
        if release:
            return CitationFileFormatConverter.convert_release(release)
    return None
