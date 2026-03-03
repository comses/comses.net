# CoMSES Net

Scholarly web platform for the Network for Computational Modeling in Social and Ecological Sciences. Community registry for computational model codebases with peer review, DOI registration (DataCite), and BagIt/OAIS archival.

**Stack:** Django 4.2 + Wagtail 5.2 + DRF 3.15 | Vue 3 + Vite 4.5 (18 island entry points) | PostgreSQL 16 + PostGIS | Elasticsearch 7 | Redis 7 + Huey | Docker Compose + uWSGI + Nginx

**Core domain:** `library/` — Codebase → CodebaseRelease lifecycle (DRAFT → UNDER_REVIEW → PUBLISHED), BagIt SIP/AIP archival, DOI minting, peer review workflow.

## Commands

### Test
`make test` — Full Django test suite in Docker
`docker compose exec server inv test --tests=library.tests.test_models` — Run specific test(s)
`docker compose run --rm server /code/deploy/test.sh library` — Test single app
`cd frontend && npm run test` — Vitest frontend tests
`make e2e` — Cypress end-to-end tests

### Dev
`make deploy` — Build + start all services
`docker compose up -d` — Start all services detached
`docker compose logs -f server` — Follow Django logs
`docker compose exec server inv sh` — Django shell (IPython)
`docker compose exec server inv db.sh` — PostgreSQL shell (pgcli)
`docker compose exec server ./manage.py` — Django CLI (migrations, management commands)
`docker compose exec vite npm run tls` — Type-check + lint + Prettier (inside vite container)
Local dev URL: http://localhost:8000

### Build
`cd frontend && npm run build` — Type-check + Vite production build
`docker compose exec server inv prepare` — Collectstatic + reindex + restart

### Lint
`cd frontend && npm run lint` — ESLint with auto-fix
`cd frontend && npm run style` — Check Prettier formatting
`cd frontend && npm run type-check` — TypeScript type-check

### Database
`docker compose exec server inv db.init` — Run migrations
`docker compose exec server inv db.reset` — Drop + recreate + migrate
`docker compose exec server inv db.shell` — Open pgcli shell

### Search
`docker compose exec server inv uindex` — Rebuild Elasticsearch index

## Project Structure

```
django/
  core/        # Users, permissions, settings, shared mixins, renderers
  library/     # Codebase repository, peer review, DOI minting, BagIt archival
  home/        # Wagtail CMS pages, site-wide search, conferences
  curator/     # Tag curation, invoke tasks, Wagtail admin hooks
  search/      # Search analytics (ArchivedQueryHits)
frontend/      # Vue 3/TS — discrete apps mount on DOM elements, NOT a SPA
```

Entry points: `django/core/settings/defaults.py` (all base config), `frontend/vite.config.ts` (auto-discovers `src/apps/*.ts`)

## Code Conventions

1. Secrets via `read_secret(key)` from `/run/secrets/{key}` — never use env vars for secrets
2. `docker-compose.yml` is generated — edit `base.yml` + overlay, then `make docker-compose.yml`
3. Jinja2 is the primary template engine; Django templates only for admin and allauth
4. Jinja2 templates live in `django/<app>/jinja2/<app>/` (app name is doubled in path)
5. camelCase JSON conversion is automatic via `CamelCaseMiddleWare` — do not manually convert in serializers
6. Only the release editor uses Vue Router + Pinia — all other Vue apps mount via `data-*` attributes
7. Owner field must be named `submitter` — `ComsesObjectPermissionBackend` checks `obj.submitter == user`
8. New permission-controlled models need `@add_to_comses_permission_whitelist` decorator
9. Tests use Django runner (`manage.py test`), not pytest — custom factories in `core/tests/base.py`
10. Task queue is Huey on Redis, not Celery — consumer must be reloaded for task/dependency changes
11. Models are fat; cross-model features go in separate modules (e.g., `library/fs.py`, `home/metrics.py`)
12. Vue components use Composition API with `<script setup>` syntax; prefer Bootstrap 5 utility classes over custom CSS
13. Forms use `vorms` (`useForm`/`useField`) wrapped in `composables/form.ts`
14. Generate migrations (`manage.py makemigrations [app]`), never hand-write them
15. E2E selectors: use `data-cy-{}` attributes, selected via `getDataCy()` in `cypress/support/util.ts`
16. `docker/shared/:/shared` volume is shared between services (library files, media, backups, JS bundles)

## Safety

Allowed without asking: read files, run single-app tests, lint, type-check, format
Ask first: `make test` (full suite), migrations, `inv prepare`, package installs, git push, delete files
Never: invoke operational tasks (`inv borg.*`, `inv db.drop`, `inv db.reset`), direct DB edits, edit generated `docker-compose.yml`

## Current State
- Branch: `main`
- Recent activity: dependency bumps (Django, Jinja2, Axios for CVEs), Vite 4.5.14
- Known debt: `queryset.update()` bypasses codemeta `save()` hooks (FIXMEs), deprecated `institution` field, `rest_framework_swagger` should be `drf-spectacular`, empty `repository/` app
- External integrations: DataCite, ORCID, GitHub OAuth, Discourse SSO, Mailgun, Sentry, hCaptcha, ROR API

## Documentation
See `agent_docs/AGENTS.md` for routing to detailed architecture, conventions, and subsystem specs.
