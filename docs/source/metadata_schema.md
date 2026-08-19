(metadata-schema)=
# CoMSES Model Library Metadata Schema

## Status and scope

This document is the normative specification for metadata stored by the CoMSES Model Library for computational models and their versioned releases. It defines the internal source-of-truth fields, lifecycle invariants, and the rules for producing external metadata records. The CodeMeta, Citation File Format (CFF), and DataCite specifications remain authoritative for their respective output formats.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as requirements on application code, data migrations, administrative operations, and background tasks.

This specification applies to:

- `Codebase`, the concept-level record for a computational model;
- `CodebaseRelease`, an immutable-after-publication version of that model;
- contributor, programming-language, platform, license, and tag relations;
- cached CodeMeta snapshots and metadata files in release packages; and
- CFF and DataCite records derived from the authoritative records.

## Conceptual model and authority

A `Codebase` describes the intellectual work across all versions. A `CodebaseRelease` describes one version and is the unit of publication, archival packaging, peer review, and version-specific DOI assignment.

Authoritative metadata MUST be read from normalized model fields and relations. `codemeta_snapshot` and generated files such as `codemeta.json` and `CITATION.cff` are derived representations; they MUST NOT be treated as independent sources of truth when editing a local record.

When sources disagree, authority is resolved in this order:

1.  the persisted `Codebase` and `CodebaseRelease` fields and relations;
2.  a validated import payload while an explicit import operation is running;
3.  cached or packaged external metadata representations.

An import MUST validate and normalize external values before updating the authoritative fields. A failed import or metadata rebuild MUST NOT leave the database, archival package, and generated metadata in a partially updated state.

## Identifiers and record identity

`Codebase.identifier` is the stable local identifier for the concept-level record. A release is locally addressed by its parent codebase and version; `CodebaseRelease.identifier`, when populated for a legacy or imported record, is an additional unique identifier. No identifier may be reused for another record.

`CodebaseRelease.version_number` MUST be a valid semantic version and MUST be unique within its codebase. It MUST NOT change after publication.

A DOI is optional until it is assigned. `Codebase.doi` identifies the concept across versions; `CodebaseRelease.doi` identifies exactly one release. DOI assignment MUST be idempotent and MUST NOT overwrite or reassign an existing DOI. Once a DOI has been exposed publicly, the DOI and its target record MUST remain stable.

`permanent_url` resolves to the DOI URL when a DOI exists and otherwise to the stable CoMSES record URL. External metadata MUST preserve the stored DOI and the resolved permanent URL when a DOI exists.

## Field registry

The registry below describes the persisted metadata contract. Fields used only for permissions, queue state, or internal file bookkeeping are outside the schema unless they affect a published representation.

### Concept-level fields (`Codebase`)

| Field                         | Cardinality  | Mutability              | Meaning and constraints                                                                                             |
|-------------------------------|--------------|-------------------------|---------------------------------------------------------------------------------------------------------------------|
| `title`                       | exactly one  | draft-editable          | Human-readable model title; maximum 300 characters.                                                                 |
| `description`                 | exactly one  | draft-editable          | Markdown source describing the model. External metadata uses the raw Markdown value.                                |
| `summary`                     | zero or one  | draft-editable          | Short description; maximum 500 characters.                                                                          |
| `identifier`                  | exactly one  | stable                  | Unique local concept identifier.                                                                                    |
| `doi`                         | zero or one  | immutable once assigned | DOI for the concept encompassing all versions.                                                                      |
| `repository_url`              | zero or one  | draft-editable          | Valid source repository URL. An active managed Git remote takes precedence when deriving `codeRepository`.          |
| `video_source_url`            | zero or one  | draft-editable          | Valid URL for a model video; current presentation support is limited to YouTube URLs.                               |
| `replication_text`            | zero or one  | draft-editable          | Citation, DOI, or URL for the model being replicated.                                                               |
| `references_text`             | zero or one  | draft-editable          | Related publication citations or DOIs.                                                                              |
| `associated_publication_text` | zero or one  | draft-editable          | Publication directly associated with the model.                                                                     |
| `tags`                        | zero or more | draft-editable          | Controlled or curated topical keywords. Serialized ordering MUST be deterministic.                                  |
| `relationships`               | zero or more | draft-editable          | Structured links to other resolvable entities. Each item MUST preserve its relationship type and target identifier. |
| `media`                       | zero or more | draft-editable          | Structured metadata for codebase-level media. Stored paths and file storage MUST remain consistent.                 |
| `first_published_at`          | zero or one  | system-managed          | Timestamp of first publication; once established it MUST be preserved.                                              |
| `last_published_on`           | zero or one  | system-managed          | Timestamp of the most recent publication event.                                                                     |

### Release-level fields (`CodebaseRelease`)

| Field or relation    | Cardinality                 | Mutability                  | Meaning and constraints                                                                                                                        |
|----------------------|-----------------------------|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `codebase`           | exactly one                 | stable                      | Parent concept record; protected from deletion while releases exist.                                                                           |
| `identifier`         | zero or one                 | stable when present         | Additional unique identifier retained for legacy or imported records; normal release routing uses the parent codebase and version.             |
| `version_number`     | exactly one                 | immutable after publication | Semantic version unique within the parent codebase.                                                                                            |
| `doi`                | zero or one                 | immutable once assigned     | DOI identifying only this release.                                                                                                             |
| `release_notes`      | zero or one                 | draft-editable              | Markdown source describing version-specific changes or run conditions; maximum 2,048 characters.                                               |
| `summary`            | zero or one                 | draft-editable              | Version-specific short description; maximum 1,000 characters.                                                                                  |
| `license`            | exactly one for publication | draft-editable              | Software license selected from the license registry.                                                                                           |
| `os`                 | exactly one for publication | draft-editable              | Supported operating-system category from the model choices.                                                                                    |
| `release_languages`  | one or more for publication | draft-editable              | Programming languages, with optional language versions.                                                                                        |
| `platform_tags`      | zero or more                | draft-editable              | Runtime frameworks or platforms; output ordering MUST be deterministic.                                                                        |
| `dependencies`       | zero or more                | draft-editable              | Structured dependency records. Recognized keys include identifier, name, version, package system, operating system, and URL.                   |
| `contributors`       | one or more for publication | draft-editable              | Ordered release contributors with roles and citation inclusion state. Person, organization, ORCID, and affiliation identity MUST be preserved. |
| `input_data_url`     | zero or one                 | draft-editable              | Valid permanent landing-page URL for input data used by the model.                                                                             |
| `output_data_url`    | zero or one                 | draft-editable              | Valid permanent landing-page URL for output data produced by the model.                                                                        |
| `embargo_end_date`   | zero or one                 | draft-editable              | End of an applicable release embargo.                                                                                                          |
| `first_published_at` | zero or one                 | system-managed              | Timestamp of the release's first publication.                                                                                                  |
| `last_published_on`  | zero or one                 | system-managed              | Timestamp of its current publication event.                                                                                                    |
| `peer_reviewed`      | exactly one                 | system-managed              | Whether this release completed the configured review process.                                                                                  |

## Publication requirements

A release MUST NOT be published unless all of the following are present and valid:

- a software license;
- at least one contributor;
- at least one programming language;
- an operating-system value;
- at least one code file; and
- at least one documentation file.

Peer-review state may impose additional publication constraints. Validation MUST run in the backend immediately before publication; client-side validation is supplementary and MUST NOT be the only enforcement point.

All external inputs, including URLs and imported metadata, MUST be validated by a serializer, form, or dedicated import validator before reaching a publication workflow. Invalid values MUST fail without changing a published record or its package.

## Lifecycle and immutability

The release states are `draft`, `under_review`, `review_complete`, `published`, and `unpublished`. State transitions MUST be explicit, auditable, and safe to retry.

A published release is an archival object. Its metadata and files MUST NOT be edited in place. Corrections or substantive changes require a new release with a new version number. A published release DOI MUST continue to resolve to the metadata for that exact version.

Unpublishing changes public visibility; it does not authorize destructive rewriting of the formerly published record or reuse of its DOI or version.

(metadata-draft-inheritance)=
## Draft inheritance

Creating a new ordinary draft from the latest release copies reusable metadata and then applies the following field-specific rules:

| Field                                                                           | New ordinary draft | Rationale                                                                                       |
|---------------------------------------------------------------------------------|--------------------|-------------------------------------------------------------------------------------------------|
| `doi`                                                                           | reset to null      | DOI assignment is version-specific.                                                             |
| `release_notes`                                                                 | reset to blank     | Release notes describe changes in the new version.                                              |
| `version_number`                                                                | replace            | Every release requires its own semantic version.                                                |
| publication timestamps and status                                               | reset              | A draft has not yet been published.                                                             |
| `input_data_url`                                                                | carry forward      | The URL identifies a permanent metadata landing page, not a version-specific uploaded artifact. |
| `output_data_url`                                                               | carry forward      | The URL identifies a permanent metadata landing page, not a version-specific uploaded artifact. |
| license, operating system, languages, platforms, dependencies, and contributors | carry forward      | These provide an editable starting point for the next version.                                  |

A review draft created from an existing release MUST preserve the source release metadata, including both data URLs, unless the review workflow explicitly defines a field-specific transformation. Copying a release MUST create a distinct database identity and MUST NOT mutate the source release.

## Data URL semantics

`input_data_url` and `output_data_url` are metadata links, not storage locations for release package files. They MUST be valid absolute URLs and SHOULD use HTTPS persistent landing pages that provide enough metadata to identify and cite the data. They MAY point to the same landing page when one dataset serves both roles.

The two roles MUST remain distinguishable in every representation. CodeMeta serializes them as `supportingData` entries in input-then-output order and includes a stable `name` discriminator:

```json
{
  "supportingData": [
    {
      "@type": "DataFeed",
      "name": "Input data",
      "url": "https://example.org/datasets/input"
    },
    {
      "@type": "DataFeed",
      "name": "Output data",
      "url": "https://example.org/datasets/output"
    }
  ]
}
```

Consumers MUST use the `name` discriminator rather than array position to identify the role. Missing URLs are omitted; an empty `supportingData` property is not emitted.

## External representation profiles

CodeMeta is the canonical external interchange representation generated from the authoritative models. Published package metadata includes CodeMeta and CFF. DOI registration metadata uses DataCite. Converters MUST avoid lossy transforms when the destination schema can represent the source value.

```{table} Key CodeMeta crosswalk

| Internal source                 | CodeMeta property                | Rule                                                                                                                        |
|---------------------------------|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| title                           | `name`                           | Inherited from the parent codebase.                                                                                         |
| permanent URL and DOI           | `@id`, `identifier`, `url`       | Use the DOI URL as the permanent URL when assigned; otherwise use the CoMSES URL. Preserve the stored DOI as an identifier. |
| description                     | `description`                    | Serialize raw Markdown.                                                                                                     |
| repository URL or active remote | `codeRepository`                 | Active managed remote takes precedence.                                                                                     |
| tags                            | `keywords`                       | Sort by name for deterministic output.                                                                                      |
| contributors and roles          | `author`, `contributor`          | Preserve ordering, roles, ORCID or local identity, and affiliation.                                                         |
| release languages               | `programmingLanguage`            | Emit `ComputerLanguage` objects.                                                                                            |
| platform tags                   | `runtimePlatform`                | Sort by name for deterministic output.                                                                                      |
| operating system                | `operatingSystem`                | Emit the stored choice value.                                                                                               |
| release notes                   | `releaseNotes`                   | Serialize raw Markdown.                                                                                                     |
| license                         | `license`                        | Emit a `CreativeWork` containing its name and URL when available.                                                           |
| version number                  | `version`                        | Emit the release semantic version.                                                                                          |
| input and output data URLs      | `supportingData`                 | Emit labeled `DataFeed` objects as specified above.                                                                         |
| publication timestamps          | `datePublished`, `copyrightYear` | Derive from the release publication event.                                                                                  |
```

Unpublished releases currently expose only minimal generated CodeMeta (`SoftwareSourceCode` type and name). Full public metadata MUST be generated synchronously during publication after the release status and publication timestamps have been set.

CFF is derived through the CodeMeta-to-CFF conversion. DataCite metadata MUST include the CoMSES publisher identity, software resource type, creators, title, version, publication year, license, and version relationships. Release relationships use `IsVersionOf`, `IsNewVersionOf`, and `IsPreviousVersionOf` as applicable; concept records use `HasVersion`.

## Snapshots, packages, and synchronization

`codemeta_snapshot` is a cache of generated CodeMeta. A normal model `save()` rebuilds the relevant snapshot. QuerySet `update()` bypasses this behavior and MUST NOT be used for metadata changes unless the caller also performs an explicit, verified rebuild.

When a release snapshot changes, the package metadata MUST be rebuilt. A deferred rebuild MUST be enqueued only after the database transaction commits. Tasks MUST accept stable record identifiers, reread current database state, and be safe to retry. Publication performs the release and codebase metadata rebuild synchronously so the public archive and database become visible in a consistent state.

Generated collections MUST have deterministic ordering so semantically unchanged metadata produces byte-stable output where the serialization format permits it. Null or empty optional properties SHOULD be omitted rather than emitted with ambiguous empty values.

## Access control

Unpublished metadata is restricted content. Views, APIs, search indexes, download endpoints, generated packages, and background tasks MUST enforce the same object-level access rules and default to denying access. A share token grants only the access explicitly implemented for that token and MUST NOT make the release generally public.

## Schema evolution and verification

Every metadata schema change MUST include:

- a reviewed database migration for persisted fields;
- serializer or form validation for externally supplied values;
- an update to this specification and the applicable crosswalk;
- regression tests for persistence, lifecycle copying or resetting, external serialization, and permissions where relevant;
- verification that published records are not rewritten in place; and
- a migration or rebuild plan when existing snapshots, packages, search documents, or DOI metadata are affected.

Tests for a new optional field MUST use a non-empty representative value. Round-trip or crosswalk tests MUST assert meaning as well as syntactic schema validity. Retry tests are REQUIRED for background operations that can affect published metadata or packages.

Changes to a published representation SHOULD preserve backward-compatible shapes where the external schema permits more than one valid encoding. When a breaking representation change is unavoidable, it MUST be documented with the affected consumers, migration strategy, and effective version or date.
