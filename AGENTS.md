# CoMSES.net Development Guide for Agents

## Overview

CoMSES.net is a web application that serves as a portal for modeling science in the social and ecological systems. The main component is the model library which archives model submissions. It also has curated resources and community postings.

## Dev environment

The app is designed to be run locally and deployed as a multi-docker-container application with `docker compose`. Always prefer doing things the "right" way as described below.

- use `make deploy` to build services and start them
- For local development, access the app at http://localhost:8000 (server service)
- a `docker-compose.yml` is composed based on the environment set in config.mk's `DEPLOY_ENVIRONMENT`
- configs are in .env and secrets are in build/secrets
- `docker/shared/:/shared` is a volume mount shared between services and holds model library files/media, backups, js bundles, etc.

Invoke (django/curator/invoke_tasks) and django management commands (django/*/management/commands) are used for many common tasks, some of the most common are:

```bash
docker compose exec server inv sh # django shell
docker compose exec server inv db.sh # postgres shell
docker compose exec server ./manage.py # django cli for running management commands, migrations, etc.
docker compose logs [server|vite|...] # see service logs
docker compose exec vite npm run tls # run vue component tests, lint, prettier
```

For backing up and restoring the database+file system use db/borg commands defined in `django/curator/invoke_tasks/`. For example, to back up a given state, restore from another, and then go back:
```bash
rm -rf docker/shared/backups/repo # delete or move the old borg repo
docker compose exec server inv db.backup borg.init borg.backup # backup the database, init repo, and create borg repo with fs + db backup
mv docker/shared/backups/repo ./working-repo # move it somewhere for safekeeping, repo/ will be root-owned
make restore # restore from whatever is in build/repo.tar.xz or at BORG_REPO_URL if build/repo.tar.xz doesn't exist
# --- do some work, now assuming we don't need to keep this current state ---
mv ./working-repo docker/shared/backups/repo # move our desired backup back
docker compose exec server inv borg.restore # and restore back
```

## Django backend (`django/`)

The backend is a wagtail (django) application that uses DRF, Postgres, ElasticSearch, Redis and Huey

- huey tasks are defined and discovered in tasks.py modules, the huey consumer runs as a seperate process in the server service, it must be reloaded for changes to tasks or their dependencies to take effect
- be mindful of the app hierarchy that seperates concerns
- models are fat, features that span many models should go in a seperate module (e.g., library/fs.py, home/metrics.py)
- Jinja2 is used for templating
- Follow PEP 8, use type hints
- Use semantic commit messages
- DRF endpoints transform snake_case into camelCase for consumption by the frontend
- generate migrations (`docker compose exec server ./manage.py makemigrations [app]`) instead of hand-writing

## Reactive frontend components (`frontend/`)

frontend/ contains vue 3 components that are mounted in pages rendered by django for interactive functionality

- written with typescript and served/bundled with vite
- Individual vue apps (`apps/`) are like widgets mounted in jinja templates
- Vue 3 Composition API with `<script setup>` syntax
- Boostrap 5 is used with some customization, always prefer bootstrap util classes over custom styling
- Pinia for global state, composables for reusable logic
- static data is passed to the components with data attributes (util.extractDataParams)
- API clients in `composables/api/`
- DRF endpoints transform snake_case into camelCase for consumption by the frontend
- We attempt to parse dates in incoming data with Date.parse() automatically but be mindful of date formatting on the server-side
- Format with prettier (npm run style:fix)
- forms use a library called `vorms` inspired by react hook form that provides useForm and useField that is wrapped in composables/form.ts

## Testing

### Django tests (`django/*/tests`)

```bash
make test # run the full suite
docker compose exec server inv test # in running container
docker compose exec server inv test --tests=library.tests.test_models # run specific tests
```

- path differences in the `test` environment/settings will cause migrations to be created/applied to the test database, these can be removed

### Cypress (`e2e/`)

for running all e2e tests with full setup:

```bash
make e2e # build e2e setup
cd e2e ; npm run test
docker compose -f docker-compose.yml -f e2e.yml down # bring services down
```

- Tests in `e2e/cypress/tests/` - covers authentication, codebase creation/editing, events, jobs, peer review
- e2e tests rely on a specific setup (see `e2e` make target) which uses the `test` environment/settings and includes a separate db container (e2edb) and a minimal backup (BORG_REPO_URL) that is assumed to match `cypress/fixtures/data.json`
- for future tests, do not rely on a specific database state
- data attributes (data-cy-{}) are preferred to select elements, see cypress/support/util.ts `getDataCy`
