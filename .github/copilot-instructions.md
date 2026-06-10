# Copilot Instructions for comses.net

## Repository Overview

This is the CoMSES.Net Computational Model Library and CMS — a Wagtail/Django backend with a Vue 3 frontend. It manages
scientific software artifacts with strict archival integrity requirements. Stack: Python/Django, Django REST Framework,
Wagtail, Vue 3 (Composition API), PostgreSQL, Redis, Elasticsearch, Docker Compose.

## Review Severity Guidance

**Blocking:**
- Archival integrity violations (immutability, DOI mutation, citation metadata changes)
- Permission bypasses or missing object-level permission enforcement
- Publication workflow correctness issues affecting published or in-review releases
- Unsafe migrations affecting published-release-related models
- Raw SQL or unsanitized input reaching model or business logic

**Major:**
- Missing tests for behavior changes to transitions, permissions, or metadata output
- Missing idempotency protections in publication or metadata background tasks
- Input validation placed outside the serializer or form layer

**Minor:**
- Non-semantic commit messages or non-linear commit history
- Small maintainability concerns (inline ORM queries, logic in views)
- Style deviations inconsistent with surrounding code

## Pull Request Review Priorities

### 1. Archival Integrity (Highest Priority)

Published model releases are immutable archival objects. Flag any code that:
- Modifies fields on a published `CodebaseRelease` or related archival model in place rather than creating a new version
- Reassigns or mutates a DOI after initial assignment
- Alters citation metadata (title, authors, version, year) on a published release
- Performs lossy transforms on metadata consumed by external systems (e.g. CodeMeta output)

These are correctness violations, not style issues. Always flag them as blocking.

### 2. Permission Enforcement

The platform uses a default-deny permission model. Flag any code that:
- Exposes unpublished or embargoed content without an explicit permission check
- Adds a new API view or serializer endpoint without verifying object-level permission enforcement
- Bypasses existing `has_object_permission` / `has_permission` patterns
- Adds permission checks only at the view layer when the same logic is accessible via the API or a background task

Cross-check permissions across views, DRF serializers/viewsets, and Huey tasks when a PR touches access-controlled
resources.

### 3. Publication and Metadata Transitions

Review/publication state transitions must be idempotent and auditable. Flag:
- Transition logic that is not safe to retry (e.g. sends external notifications or mutates files without a guard against
  double-execution)
- Missing audit trail for state changes (no log, no signal, no history record)
- Background tasks (Huey) that affect publication state but lack idempotency guards

### 4. Django Migrations

- Auto-generated migrations should be reviewed for unintended side effects (field renames misdetected as drop+add, data
  migrations missing, reverse migration not defined)
- Hand-written migrations require extra scrutiny: flag if data migrations don't handle empty querysets gracefully or
  lack a `RunPython(..., reverse_code=migrations.RunPython.noop)`
- Flag any migration that alters fields on published-release-related models without a corresponding immutability
  review

### 5. Input Validation Placement

Validation and sanitization must occur at the serializer or form layer before reaching model or business logic. Flag:
- Validation logic added directly to model `save()` methods that should live in a serializer
- Raw user input reaching ORM queries without serializer-layer validation
- Raw SQL without explicit justification

### 6. Backend Conventions

- Complex or reusable query logic belongs in QuerySet methods on model managers, not constructed inline at call sites.
  Flag significant inline ORM query construction.
- New cross-model workflows should live in dedicated modules, not spread across views. Flag views with substantial
  business logic that should be extracted.
- Flag any code that introduces a new third-party dependency without clear justification in the PR description.

### 7. Frontend (Vue 3)

- All new components must use Vue 3 Composition API with `<script setup>`. Flag Options API usage in new files.
- API client logic belongs in composables. Flag components making direct `fetch`/`axios` calls.
- Flag assumptions about date formats from API responses — the API uses snake_case keys that are transformed to
  camelCase; flag any code that accesses properties using the wrong case convention.
- Prefer CSS framework utility classes (currently Bootstrap 5.x); flag new custom CSS that duplicates an available utility.

### 8. Test Coverage

Flag PRs that:
- Change behavior of published-release transitions, permission checks, or metadata output without adding or updating
  tests
- Fix a bug without a regression test
- Introduce nontrivial query logic in a manager or composable without unit test coverage

The test runner is `make test TEST_ARGS=<dotted.test.path>`. Flag PRs where the described change is not covered by a
test that can be run with this command.

## Key Locations

- `django/library/` — Django models for codebase and codebase release metadata, peer review and publication workflows, DOI minting and CodeMeta generation
- `django/library/tasks.py` - Huey tasks for async workflows related to the Model Library, including DOI minting and publication state transitions
- `django/home/` — Wagtail CMS pages and content types
- `django/core/` — shared Django models, permissions, and platform utilities
- `frontend/src/` — Vue 3 application with semantic directory structure

When a PR touches publication or permission logic, check for parallel implementations across views, serializers, and
Huey tasks — they must all enforce the same rules.

## What Not to Flag

- Minor style deviations that are consistent with the surrounding file's existing style
- Absence of docstrings on straightforward methods
- CSS class ordering
- Prefer leaving judgment calls about refactoring scope to human reviewers unless the PR introduces clear technical debt
  risk

## Commit and PR Conventions

PRs should use semantic commit messages with clean, linear commit history; flag commits with non-semantic messages as a minor/informational note.

## Useful Context

- `docs/agents/commands.md` — canonical command index
- `docs/agents/` — runbooks and operational context