# Copilot Instructions for comses.net

## Repository Overview

This is the CoMSES.Net Science Gateway, an open repository and publication platform for computational models and research software used in social, ecological, and earth sciences.

The platform supports model publication, peer review, DOI minting, metadata preservation, discovery, and long-term archival access. Published model releases are treated as immutable scholarly artifacts and must preserve citation and provenance integrity.

**Stack:** Python/Django, Django REST Framework, Wagtail, Vue 3 (Composition API), PostgreSQL, Redis, Elasticsearch,
Docker Compose.

**Glossary:**
- **CodeMeta** — the metadata standard emitted for consumption by external systems.
- **Codebase / CodebaseRelease** — core archival models; a release is a versioned, citable artifact.
- **Huey** — the asynchronous task queue used for background jobs (DOI minting, publication state transitions, metadata generation).

## Review Philosophy

- Prefer fewer, higher-confidence comments over exhaustive nitpicking.
- A correctness or security concern always outweighs a style or maintainability note.
- Tag every comment with a severity prefix: `[Blocking]`, `[Major]`, or `[Minor]`. If a finding doesn't clearly map to
  one, default to a non-blocking `[Minor]` note.
- **Limits:** When a check requires repo-wide knowledge, cross-file parity, migration data state, or runtime behavior
  that is not visible in the diff, raise it as a question rather than a definitive finding. Do not assert that a test,
  permission check, or parallel implementation is missing if you cannot see the relevant code.
- Leave judgment calls about refactoring scope to human reviewers unless the PR introduces clear technical-debt or
  correctness risk.

## Severity Definitions

- **Blocking** — must be resolved before merge: archival integrity violations, permission bypasses, publication
  workflow correctness issues, unsafe migrations on published-release models, raw SQL or unsanitized input reaching
  model/business logic.
- **Major** — should be addressed before merge: missing tests for behavior changes, missing idempotency protections in
  publication/metadata tasks, validation placed outside the serializer/form layer.
- **Minor** — informational or follow-up: non-semantic commit messages, small maintainability concerns (inline ORM
  queries, logic in views), style deviations inconsistent with surrounding code.

## Pull Request Review Priorities

Each section below carries its own severity. When in doubt, see the Severity Definitions above.

### 1. Archival Integrity — Blocking

Published model releases are immutable archival objects. Flag any code that:
- Modifies fields on a published `CodebaseRelease` or related archival model in place rather than creating a new version
- Reassigns or mutates a DOI after it has been registered/minted (draft or pre-registration DOI workflows, if any, are
  out of scope for this rule)
- Alters citation metadata (title, authors, version, year) on a published release
- Performs lossy transforms on metadata consumed by external systems (e.g. CodeMeta output)

These are correctness violations, not style issues.

### 2. Permission Enforcement — Blocking

The platform uses a default-deny permission model. Flag any code that:
- Exposes unpublished or embargoed content without an explicit permission check
- Adds a new API view or serializer endpoint without object-level permission enforcement
- Bypasses existing `has_object_permission` / `has_permission` patterns
- Adds permission checks only at the view layer when the same logic is reachable via the API or a background task

When a PR touches access-controlled resources, cross-check permissions across views, DRF serializers/viewsets, and Huey
tasks — they must all enforce the same rules. If you cannot see all three layers in the diff, flag the ones you can and
note that parity should be confirmed by a human reviewer.

### 3. Publication and Metadata Transitions — Blocking (correctness) / Major (missing guards or audit trail)

Review/publication state transitions must be idempotent and auditable. Flag:
- Transition logic that is not safe to retry (e.g. sends external notifications or mutates files without a guard against
  double-execution) — **Blocking**
- Background tasks (Huey) that affect publication state but lack idempotency guards — **Blocking**
- Missing audit trail for state changes (no log, no signal, no history record) — **Major**

### 4. Django Migrations

- Review auto-generated migrations for unintended side effects (field renames misdetected as drop+add, missing data
  migrations, undefined reverse migration). **Major**
- Hand-written migrations require extra scrutiny: flag if data migrations don't handle empty querysets gracefully or
  lack an appropriate reverse migration strategy (e.g., a real reverse migration or RunPython.noop where reversal is intentionally unsupported)
- Flag any migration that alters fields on published-release-related models without a corresponding immutability
  review. **Blocking**

### 5. Input Validation Placement — Blocking (unsanitized input / raw SQL) / Major (placement)

Validation and sanitization must occur at the serializer or form layer before reaching model or business logic. Flag:
- Raw user input reaching ORM queries or raw SQL without serializer-layer validation/sanitization — **Blocking**
- Validation logic added directly to model `save()` methods that should live in a serializer — **Major**
- Raw SQL that is properly parameterized but added without justification in the PR description — **Minor** (ask for
  rationale)

### 6. Backend Conventions — Minor unless noted

- Complex or reusable query logic belongs in QuerySet methods on model managers, not constructed inline at call sites.
  Flag significant inline ORM query construction.
- New cross-model workflows should live in dedicated modules, not spread across views. Flag views with substantial
  business logic that should be extracted.
- Flag any code that introduces a new third-party dependency without clear justification in the PR description.

### 7. Frontend (Vue 3) — Minor unless it causes a correctness bug

- All new Vue components should use the Composition API with `<script setup>`. Do not request conversion of existing Options API components unless the PR is already performing a substantial rewrite.
- API client logic belongs in composables. Flag components making direct `fetch`/`axios` calls.
- API responses use snake_case keys that are transformed to camelCase by the shared API response transform. Flag code
  that accesses properties using the wrong case convention relative to where the transform is (or is not) applied. If
  it's unclear whether the transform applies at a given call site, raise it as a question.
- Prefer CSS framework utility classes (currently Bootstrap 5.x); flag new custom CSS that duplicates an available
  utility.

### 8. Test Coverage — Major

Flag PRs where the diff changes behavior but does not include corresponding test additions or updates, specifically for:
- Published-release transitions, permission checks, or metadata output
- Bug fixes lacking a regression test
- Nontrivial query logic in a manager or composable lacking unit test coverage

The test runner is `make test TEST_ARGS=<dotted.test.path>`. Base this on what is visible in the diff; do not assert
that a runnable test is missing if the relevant test files are not part of the change.

## Key Locations

- `django/library/` — Django models for codebase and codebase release metadata, peer review and publication workflows,
  DOI minting and CodeMeta generation
- `django/library/tasks.py` — Huey tasks for async Model Library workflows, including DOI minting and publication state
  transitions
- `django/home/` — Wagtail CMS pages and content types
- `django/core/` — shared Django models, permissions, and platform utilities
- `frontend/src/` — Vue 3 application with semantic directory structure

When a PR touches publication or permission logic, check for parallel implementations across views, serializers, and
Huey tasks — they must all enforce the same rules.

## What Not to Flag

- Minor style deviations consistent with the surrounding file's existing style
- Absence of docstrings on straightforward methods
- CSS class ordering
- Refactoring-scope judgment calls, unless the PR introduces clear technical-debt or correctness risk

## Commit and PR Conventions

PRs should use semantic commit messages with a clean, linear commit history. Flag non-semantic commit messages as a
`[Minor]` / informational note.

## Useful Context

- `docs/agents/commands.md` — canonical command index
- `docs/agents/` — runbooks and operational context