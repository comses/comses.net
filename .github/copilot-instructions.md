# AGENTS.md

## Commands

### Test
`make test` — Full Django test suite in Docker
`docker compose run --rm server /code/deploy/test.sh library` — Test single app
`cd frontend && npm run test` — Vitest frontend tests
`make e2e` — Cypress end-to-end tests

### Dev
`make deploy` — Build + start all services
`docker compose up -d` — Start all services detached
`docker compose logs -f server` — Follow Django logs

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
10. Task queue is Huey on Redis, not Celery

## Safety

Allowed without asking: read files, run single-app tests, lint, type-check, format
Ask first: `make test` (full suite), migrations, `inv prepare`, package installs, git push, delete files
Never: invoke operational tasks (`inv borg.*`, `inv db.drop`, `inv db.reset`), direct DB edits, edit generated `docker-compose.yml`
