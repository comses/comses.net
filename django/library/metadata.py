from datetime import date
from typing import Literal
from codemeticulous.codemeta.models import (
    CodeMeta,
    Person,
    Organization,
    Role,
    CreativeWork,
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
    def convert_release_contributors(
        cls,
        release_contributors,
        actor_type: Literal["author", "contributor"],
    ) -> list[Person | Organization | Role]:
        codemeta_actors = []
        codemeta_roles = []
        for num, rc in enumerate(release_contributors):
            contributor = rc.contributor
            # https://www.w3.org/TR/json-ld11/#identifying-blank-nodes
            contributor_id = contributor.orcid_url or f"_:{actor_type}_{num + 1}"
            if contributor.is_organization:
                codemeta_actors.append(
                    Organization(
                        id_=contributor_id,
                        name=contributor.name,
                    )
                )
            elif contributor.is_person:
                affiliation = (
                    cls.convert_affiliation(contributor.primary_affiliation)
                    if contributor.primary_affiliation
                    else None
                )
                codemeta_actors.append(
                    Person(
                        id_=contributor_id,
                        givenName=contributor.get_given_name() or None,
                        familyName=contributor.get_family_name() or None,
                        affiliation=affiliation,
                        email=contributor.email or None,
                    )
                )

            for role in rc.roles:
                if role != "author":
                    codemeta_roles.append(
                        Role(
                            id_=contributor_id,
                            roleName=role,
                        )
                    )

        return codemeta_actors + codemeta_roles

    @classmethod
    def to_textual_creative_work(cls, text: str) -> CreativeWork:
        return {
            "@type": "CreativeWork",
            "text": text,
        }

    @classmethod
    def _convert_release(cls, release) -> CodeMeta:
        codebase = release.codebase
        return CodeMeta(
            type_="SoftwareSourceCode",
            id_=release.permanent_url,
            identifier=(
                [release.doi, release.permanent_url]
                if release.doi
                else release.permanent_url
            ),
            name=codebase.title,
            # FIXME: is this semantically correct?
            # isPartOf=COMSES_MODEL_LIBRARY_CREATIVE_WORK,
            codeRepository=codebase.repository_url or None,
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
            applicationCategory="Computational Model",
            # applicationSubCategory="Agent-Based Model", <-- would be nice
            downloadUrl=f"{settings.BASE_URL}{release.get_download_url()}",
            operatingSystem=release.os,
            releaseNotes=release.release_notes.raw,
            supportingData=release.output_data_url or None,
            author=cls.convert_release_contributors(
                release.author_release_contributors, "author"
            )
            or None,
            citation=[
                cls.to_textual_creative_work(text)
                for text in [
                    codebase.references_text,
                    codebase.replication_text,
                ]
                if text
            ]
            or None,
            contributor=cls.convert_release_contributors(
                release.nonauthor_release_contributors, "contributor"
            )
            or None,
            copyrightYear=(
                release.last_published_on.year if release.last_published_on else None
            ),
            dateCreated=codebase.date_created.date(),
            dateModified=(
                release.last_modified.date() if release.last_modified else None
            ),
            datePublished=(
                release.last_published_on.date() if release.last_published_on else None
            ),
            # tags are sorted so that comparisons are deterministic
            keywords=[tag.name for tag in codebase.tags.all().order_by("name")] or None,
            license=release.license.url if release.license else None,
            publisher=cls.COMSES_ORGANIZATION,
            version=release.version_number,
            description=codebase.description.raw,
            url=release.permanent_url,
            embargoEndDate=release.embargo_end_date,
            referencePublication=codebase.associated_publication_text or None,
        )

    @classmethod
    def _convert_release_minimal(cls, release) -> CodeMeta:
        codebase = release.codebase
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
            logger.exception("Error when generating codemeta: %s", e)
            return cls._convert_release_minimal(release)

    @classmethod
    def convert_codebase(cls, codebase) -> CodeMeta:
        # TODO: finish this, should extract common stuff from create_release
        return CodeMeta(
            type_="SoftwareSourceCode",
            id_=codebase.permanent_url,
            name=codebase.title,
            publisher=cls.COMSES_ORGANIZATION,
        )


class CitationFileFormatConverter:
    """Create citation file format objects that represent the metadata for a codebase or release."""

    @classmethod
    def convert_release(
        cls, release, codemeta: CodeMeta | dict = None
    ) -> CitationFileFormat:
        if not codemeta:
            codemeta = CodeMetaConverter.convert_release(release)
        elif isinstance(codemeta, dict):
            try:
                codemeta = CodeMeta(**codemeta)
            except:
                codemeta = None
        return convert("codemeta", "cff", codemeta)


class DataCiteConverter:
    """Create datacite metadata objects that represent the metadata for a codebase or release."""

    @classmethod
    def convert_release(cls, release, codemeta: CodeMeta | dict = None) -> DataCite:
        if not codemeta:
            codemeta = CodeMetaConverter.convert_release(release)
        elif isinstance(codemeta, dict):
            try:
                codemeta = CodeMeta(**codemeta)
            except:
                codemeta = None
        # datacite always needs a publication date
        if not codemeta.datePublished:
            codemeta.datePublished = date.today()
        # any additional fields that cannot be derived from codemeta
        addl_datacite_fields = {}
        return convert("codemeta", "datacite", codemeta, **addl_datacite_fields)

    @classmethod
    def convert_codebase(cls, codebase, codemeta: CodeMeta | dict = None) -> DataCite:
        if not codemeta:
            codemeta = CodeMetaConverter.convert_codebase(codebase)
        elif isinstance(codemeta, dict):
            try:
                codemeta = CodeMeta(**codemeta)
            except:
                codemeta = None
        # datacite always needs a publication date
        if not codemeta.datePublished:
            codemeta.datePublished = date.today()
        # any additional fields that cannot be derived from codemeta
        addl_datacite_fields = {}
        return convert("codemeta", "datacite", codemeta, **addl_datacite_fields)
