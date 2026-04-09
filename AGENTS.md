# CoMSES.Net Agent Guide

## Agent Operating Principles

This file defines mandatory rules for coding agents working in this repository.

Decision priority:

1. Security, correctness, and data integrity
2. Maintainability and readability
3. Consistency with existing patterns

General approach:

- Make minimal, focused changes
- Do not refactor unrelated code
- Prefer extending existing patterns over introducing new abstractions
- Avoid duplicate logic; centralize reusable behavior
- If requirements are ambiguous, choose the simplest correct solution and state assumptions or ask for more input
- Do not introduce new dependencies or architectural patterns without clear justification

## Domain Invariants

This platform manages scientific software artifacts and publication metadata. The following are non-negotiable:

- Published model releases are immutable archival objects
- Never modify published artifacts in place; create a new version
- DOI assignment is version-specific and must not be changed retroactively
- Citation metadata must remain accurate and stable for each published version
- Metadata is consumed by external systems; preserve schema integrity and avoid lossy transforms
- Review and publication transitions must be explicit, auditable, and safe to retry without side effects (idempotent)
- File storage and database state must remain consistent; avoid partial updates
- Background tasks that affect publication or metadata must be safe to retry
- Permission checks must be enforced in the backend at object level
- Ensure consistent permission enforcement across views, APIs, and background tasks
- Default deny: do not expose restricted or unpublished content without explicit authorization

## Security and Engineering Baseline

- Follow OWASP Top 10 and ASVS principles
- Validate and sanitize all external inputs at the serializer or form layer before reaching model or business logic
- Avoid raw SQL unless explicitly justified and reviewed
- Protect sensitive data; never expose secrets in code or responses
- Reuse existing permission and role-checking patterns
- When in doubt, choose the more secure implementation

## Backend Conventions (Django)

- Keep core domain logic in models; place cross-model workflows in dedicated modules
- Put reusable or nontrivial query logic in QuerySet methods and expose via model managers
- Compose QuerySet methods at call sites; avoid constructing complex ORM queries inline
- Do not bypass ORM, serializers, or permissions without explicit justification
- Generate migrations; do not hand-write migration files unless required and always review auto-generated migrations before committing
- Huey task changes may require consumer restart

## Frontend Conventions (Vue)

- Use Vue 3 Composition API with script setup
- Prefer Bootstrap utility classes before custom styling
- Keep API client logic in composables
- Ensure API shape compatibility with snake_case to camelCase transformations
- Be careful with date parsing assumptions from API responses

## Testing Expectations

- Add or update tests for behavior changes, bug fixes, and nontrivial logic
- Prefer targeted test execution during development
- Use repository-standard containerized commands for running tests and tooling
- Do not change existing behavior without updating or adding tests

## Environment and Commands

- Use Docker Compose workflow for local development
- Store agent runbooks, plans, checkpoints, and handoff artifacts in `docs/agents/`
- Keep reusable templates in `docs/agents/templates/`
- See `docs/agents/commands.md` for a minimal command index used by humans and agents
- Prefer repo-root-relative paths for links (for example, `docs/agents/commands.md`), not machine-absolute paths (for example, `/home/...`).
- Keep operational runbooks, backup and restore procedures, and full command catalogs in project docs
- Keep this file policy-focused; avoid long procedural walkthroughs
