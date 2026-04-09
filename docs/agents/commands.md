# Command Index For Humans And Agents

This page is a minimal index of commonly used operational commands.

## Environment Quick Context

- Local app URL: http://localhost:8000 (server service)
- Compose environment is selected via config.mk DEPLOY_ENVIRONMENT (dev, staging, test, prod)
- Runtime config is in .env and secrets are in build/secrets
- Shared volume docker/shared/:/shared stores model files, media, backups, and bundles
- Canonical deployment procedures: docs/source/deployment.rst

Guidelines:

- Run project commands from the repository root.
- Prefer containerized commands via Docker Compose.
- Do not store secrets in shell history or docs.

## Common Development Commands

```bash
docker compose exec server inv sh # django shell
docker compose exec server inv db.sh # postgres shell
docker compose exec server ./manage.py # django management commands, migrations, etc.
docker compose logs [server|vite|...] # service logs
docker compose exec vite npm run tls # vue tests, lint, prettier
```

## Backup And Restore Workflow (Borg)

```bash
mv docker/shared/backups/repo "$(mktemp -d /tmp/comses.XXXXXX)"

docker compose exec server inv db.backup borg.init borg.backup # backup db + fs into borg repo

mv docker/shared/backups/repo ./working-repo # move repo somewhere safe

make restore # restore from build/repo.tar.xz or BORG_REPO_URL

# --- do some work, now assuming we do not need to keep this current state ---

mv ./working-repo docker/shared/backups/repo # move desired backup back

docker compose exec server inv borg.restore # restore to saved state
```

## Django Test Commands

```bash
make test # full suite
docker compose exec server inv test # test suite in running container
docker compose exec server inv test --tests=library.tests.test_models # targeted tests
```

## Cypress E2E Commands

```bash
make e2e # build e2e setup
cd e2e ; npm run test
docker compose -f docker-compose.yml -f e2e.yml down # bring services down
```

## Notes

- The e2e setup depends on the test environment and fixtures.
- Future tests should not assume a fixed database state.
- For long-form operational procedures, keep canonical runbooks in project docs and link from here.
