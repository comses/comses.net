# Command Index For Humans And Agents

This page is a minimal index of commonly used operational commands.

## Environment Quick Context

- Local app URL: http://localhost:8000 (server service)
- Compose environment is selected via config.mk DEPLOY_ENVIRONMENT (dev, staging, test, prod)
- Deployed commands run from `/srv/apps/comses`; local commands run from the checkout root
- Deployed shared state is `/srv/apps/comses/docker/shared`; PostgreSQL is isolated at `/srv/apps/comses/docker/pgdata`
- Logs are `/srv/logs/comses`, and secrets are `/srv/apps/comses/docker/secrets`
- Full storage and migration contract: `docs/agents/storage-layout.md`
- Backup and restore runbook: `docs/agents/backup-restore-runbook.md`
- Canonical deployment procedures: docs/source/deployment.md

Guidelines:

- Run project commands from the repository root.
- Prefer containerized commands via Docker Compose.
- Do not store secrets in shell history or docs.

## Common Development Commands

```bash
docker compose exec server inv sh # django shell
docker compose exec server inv db.sh # postgres shell
docker compose exec server ./manage.py # django management commands, migrations, etc.
docker compose exec server inv db.make-migrations # explicitly generate migration files
docker compose logs [server|vite|...] # service logs
docker compose exec vite npm run tls # vue tests, lint, prettier
```

## Backup And Restore Workflow (Borg)

For a fresh installation, rebuild or recovery drill, use the application-owned
[seed provisioning workflow](seed-provisioning.md). It pairs an explicit seed
with an exact checked-out release and holds activation separately:

```bash
python3 deploy/scripts/provision-from-seed --help
make test-seed-provisioning # unprivileged workflow contracts; no database reset
```

See `docs/agents/backup-restore-runbook.md` before restoring production state.

```bash
docker compose exec server inv borg.init borg.backup-all # locked, validated DB + filesystem backup
docker compose exec server inv borg.list # list available restore points
docker compose exec server inv borg.prune # preview only; no pruning or compaction
docker compose exec server inv borg.restore --archive="<archive>" # destructive full restore
make restore # destructive local restore from packaged/downloaded Borg repository
```

Infrastructure pulls the staging replica from the backup host. Its source exporter
reads the host-visible repository under the existing application and Borg locks;
there is no application replication command or container replication credential.
Use the infrastructure rollout and maintenance procedures linked from
`docs/agents/borg-replication-design.md` for pull, verification and reconciliation.

Retention is operator-initiated maintenance. Applying pruning also compacts the
local repository and requires confirmation. Infrastructure owns the recovery
checkpoints and subsequent replica reconciliation and verification. Follow the maintenance
section in `docs/agents/backup-restore-runbook.md`; the application does not
verify cloud snapshots or update the replica by itself.

## Django Test Commands

```bash
make test # full suite
docker compose exec server inv test # test suite in running container
docker compose exec server inv test --tests=library.tests.test_models # targeted tests
```

## Deployment Test Commands

```bash
make test-deploy-contracts # unprivileged Makefile command and shutdown contracts
make test-storage-scripts # privileged disposable storage ownership/mount checks
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
