from typing import Literal
from codemeticulous.codemeta.models import CodeMeta, Person, Organization, Role

from django.conf import settings

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


def convert_affiliation(affiliation: dict):
    return Organization(
        id_=affiliation.get("ror_id") or None,
        name=affiliation.get("name"),
        url=affiliation.get("url"),
        identifier=affiliation.get("ror_id") or None,
    )


def convert_release_contributors(
    release_contributors,
    actor_type: Literal["author", "contributor"],
):
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
                convert_affiliation(contributor.primary_affiliation)
                if contributor.primary_affiliation
                else None
            )
            codemeta_actors.append(
                Person(
                    id_=contributor_id,
                    givenName=contributor.given_name,
                    familyName=contributor.family_name,
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


def to_textual_creative_work(text: str):
    return {
        "@type": "CreativeWork",
        "text": text,
    }


def release_to_codemeta(release):
    codebase = release.codebase
    return CodeMeta(
        **{"@context": "https://doi.org/10.5063/schema/codemeta-2.0"},
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
        codeRepository=(
            codebase.git_mirror.remote_url
            if codebase.git_mirror
            else codebase.repository_url
        )
        or None,
        programmingLanguage=[
            # FIXME: this can include "version" when langs are refactored
            {"@type": "ComputerLanguage", "name": pl.name}
            for pl in release.programming_languages.all()
        ],
        runtimePlatform=[tag.name for tag in release.platform_tags.all()] or None,
        # FIXME: anything to use this for? it can be either the target os or target
        # framework (e.g. Mesa, NetLogo) but these are both already covered
        # targetProduct=release.os,
        applicationCategory="Computational Model",
        # applicationSubCategory="Agent-Based Model", <-- would be nice
        downloadUrl=f"{settings.BASE_URL}{release.get_download_url()}",
        operatingSystem=release.os,
        releaseNotes=release.release_notes.raw,
        supportingData=release.output_data_url or None,
        author=convert_release_contributors(
            release.author_release_contributors, "author"
        )
        or None,
        citation=[
            to_textual_creative_work(text)
            for text in [
                codebase.references_text,
                codebase.replication_text,
            ]
            if text
        ]
        or None,
        contributor=convert_release_contributors(
            release.nonauthor_release_contributors, "contributor"
        )
        or None,
        copyrightYear=(
            release.last_published_on.year if release.last_published_on else None
        ),
        dateCreated=codebase.date_created.date(),
        dateModified=release.last_modified.date(),
        datePublished=(
            release.last_published_on.date() if release.last_published_on else None
        ),
        keywords=[tag.name for tag in codebase.tags.all()] or None,
        license=release.license.url if release.license else None,
        publisher=COMSES_ORGANIZATION,
        version=release.version_number,
        description=codebase.description.raw,
        url=release.permanent_url,
        embargoEndDate=release.embargo_end_date,
        referencePublication=codebase.associated_publication_text or None,
    )
