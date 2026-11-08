# Application deployment preflight

The operator deployment entrypoint remains infrastructure's `make comses-deploy`.
The application exposes one reusable check interface:

```sh
make deploy-preflight
```

Run it from the canonical checkout with its existing `config.mk` and `.env`.
It does not generate secrets/configuration, build or pull images, change source,
or start/stop services. Missing configuration is an error. The storage check
uses permission inspection rather than creating write probes in this mode.
It must be the sole Make goal; combining it with deployment or other goals is
rejected before recipes run.
The command is also suitable for application checks before maintenance or reboot;
it does not itself authorize either operation or run automatically during them.

## Contract and ownership

| Invariant | Owner | Check / limit |
| --- | --- | --- |
| Intended host, operator and environment | Infrastructure | SSH routing, identity and environment-qualified target |
| Known, accepted source | Infrastructure | Clean canonical checkout, release on main, exact staging QA SHA for production |
| Recovery readiness and operation exclusion | Infrastructure | Fresh application backup marker and shared backup/restore lock |
| Intended durable storage | Application | Mounts, ownership/access, canonical bind aliases and PostgreSQL authority |
| Candidate uses that storage and environment | Application | Render selected Compose overlays; verify writable core DB, Redis and application binds and Django settings |
| No competing foreign writers | Application | Inspect the same Docker command/context; reject active or restartable foreign writable mounts overlapping protected roots |
| Bounded resource demand | Application configuration and acceptance | Worker ceilings and Redis timeout tests; these do not prove total live DB consumption or representative-load capacity |
| Successful transition | Infrastructure plus functional QA | Exact resulting revision, clean source, running services and Django checks; operator functional acceptance remains necessary |

`deploy/scripts/storage-layout.sh` owns root defaults, image-user IDs, expected
paths and overlay selection. Make, storage preparation, storage validation and
ownership inspection use it. Known canonical log/backup aliases are included
explicitly because resolving symlinks does not identify bind mounts.

`deploy/scripts/deploy-preflight` coordinates the checks and reports independent
failures together. Existing storage/ownership scripts are implementation
components; operators do not need to assemble their own sequence. Resolved
Compose configuration may contain secrets and is never printed by the runner.
Failures identify the invariant and relevant storage paths, not credential values.

## Deployment order

1. Infrastructure selects the exact candidate and runs its application preflight.
2. Under infrastructure's operation lock, `make deploy` checks source Compose
   configuration and current storage/ownership before building.
3. The normal application build renders Compose into a private (`0600`) temporary
   file, replaces `docker-compose.yml` only on success, and builds/pulls images.
   Failed rendering preserves the previous configuration for operational commands.
4. Preflight repeats against the **generated** `docker-compose.yml` immediately
   before `up`; newly conflicting owners or changed storage block service startup.
5. The normal preparation and infrastructure postflight run, followed by QA.

Overlay selection is shared. The early check renders configuration in memory;
the normal build writes the deployment configuration; the final check validates
that generated file. Build and runtime commands explicitly select
`docker-compose.yml`, so automatic override-file discovery and `COMPOSE_FILE`
cannot substitute an unchecked configuration. Source rendering selects the
shared overlay list explicitly; E2E commands explicitly add their test overlay.
These are distinct observations, not a claim that state cannot change between
them. Direct Docker operations and non-cooperating operators remain outside the
backup/deployment lock.

Infrastructure previews may extract the selected release's Makefile, scripts and
Compose inputs into a temporary directory and invoke `make deploy-preflight`
with `DEPLOY_SCRIPTS_DIR` and `COMPOSE_SOURCE_ROOT` pointing there. The physical
project directory, protected environment and storage still belong to the real
canonical checkout. A preview must not run the old checkout's checks while
claiming to validate a newer candidate. It must not remake `.env` or `config.mk`.

PostgreSQL files may be bind-mounted only by `db`. Candidate preflight and the
standalone storage verifier share this rule, rejecting mounts of the PostgreSQL
root, its parents or descendants on any other service, even when read-only.
Paths are normalized and symlinks resolved; unrelated sibling paths are allowed.
This checks Docker bind mounts, not the host mounts provisioned by infrastructure.

## Deliberate limits

The ownership policy exempts containers only when both their Compose project name
and normalized working-directory label match the canonical deployment directory.
Missing directory labels and same-name containers from other checkouts receive no
exemption. Temporary preview source directories do not change this identity.
It permits read-only foreign consumers and rejects foreign writers, including writers to
collaborative log/backup roots. It does not prove one process per database, inspect
host processes, discover arbitrary bind aliases or prevent privileged bypass.
Stopped containers with a restart policy are conservatively checked even when
that policy would keep a manually stopped container stopped. The diagnostic reports
the observed state and policy; it does not predict that every such container will
restart on boot. Labels are not an authentication boundary.
Any legitimate foreign writer needs an explicit policy review; do not add a
blanket skip switch. This contract does not replace database privilege separation,
load testing, data-compatible rollback planning or functional recovery testing.

Validation: `make test-deploy-contracts` exercises command selection, path aliases,
configuration bindings, failure aggregation, read-only preview and both deployment
gates. `make test-storage-scripts` tests actual ownership and bind-mount fixtures.

Storage defaults for staging and production use `/srv/apps/comses`, matching
infrastructure provisioning, rather than the caller's current directory.
Non-canonical installations must explicitly configure and review their storage
paths and expected-path overrides. Make resolves defaults once and stops if the
layout helper fails; explicit operator overrides are preserved.

If Compose rendering fails, preflight reports the operation and exit status (or
filesystem error) without dumping configuration or subprocess output. Ownership
inspection is skipped with an explicit diagnostic because the candidate project
identity is unavailable; it never guesses a project name.

Contract tests run the real Make/preflight CLI with disposable storage-check and
Docker fixtures, including temporary-source preview, the final rendered-file gate,
and a competing writer appearing after build. They do not start containers.
