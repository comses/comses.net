# Provision from an explicit seed and a pinned release

This is the application side of the shared provisioning contract: restore seed X
with release Y, validate it, and hold activation for separate operator approval.
Initial staging, a production rebuild and an ephemeral drill use the same
application phases. Environment-specific credentials and infrastructure state
remain separate. This workflow currently accepts a prepared Borg seed containing
a custom-format database dump. It does not publish minimal or sanitized seeds.

## Responsibility boundary

| Owner | Responsibilities |
| --- | --- |
| Infrastructure repository | Cloud resources and quotas; networks; operator authority and SSH trust; verified disk identification, formatting and mounting; shared container runtime; application checkout pin; verified snapshot/clone selection; local working repository delivery; handoff and independent evidence export; ephemeral resource teardown. |
| This application release | Storage ownership/layout helpers; application prerequisites; configuration and fresh generated secrets; Compose/build/runtime requirements; seed identity and dump compatibility checks; existing Borg restore and migrations; application validation; safe application profile and activation policy. |
| Operator | Approve seed, release and destination; review seed evidence and data sensitivity; authorize data replacement; inspect failures and explicitly authorize destructive retries; perform functional acceptance; approve activation independently; retain evidence and close the drill. |

Infrastructure invokes this release's entry point. It must not reimplement image
selection, Compose service commands, Django settings, restore logic, migrations
or application secret generation. The application does not identify Cinder
devices, manage SSH trust, create/delete snapshots or borrow cloud credentials.
The target identity supplied to the application is an infrastructure attestation;
the application additionally binds execution to the mounted `/srv` filesystem
UUID. It does not independently authenticate a cloud instance UUID.

## Handoff

Infrastructure supplies an exact checked-out commit, a verified writable target
with prepared application storage, and a local working copy of the selected Borg
repository at the application's `/shared/backups/repo` mount. Keep the source
snapshot clone read-only. Do not restore directly from that clone: Borg requires
writable lock state. Do not copy the clone's credentials or run its executables.
The working repository must be exclusively owned by this provisioning window;
stale copied Borg lock files require an independently reviewed resolution before
inspection. The workflow never breaks locks automatically.

Supply a non-secret JSON seed manifest with exactly these keys:

```json
{
  "schema": 1,
  "kind": "borg",
  "repository_id": "<64-character Borg repository ID>",
  "archive": "<exact archive name>",
  "archive_id": "<64-character archive fingerprint>",
  "evidence_ref": "<absolute evidence path or URN>"
}
```

`evidence_ref` points to independent integrity/provenance evidence owned by
infrastructure; it contains no credentials. Snapshot, clone and source-volume IDs
belong in that evidence, not in application-specific cloud logic. A replica
becomes an explicit seed by selecting this exact archive and fingerprint; there
is no implicit latest archive. The application rechecks repository and archive
IDs against the delivered working copy.
Use `--seed -` to receive the manifest as JSON on stdin; all child commands have
stdin disabled independently, so Compose cannot consume the remaining input.

The seed's evidence and compatibility with a release are different claims.
Inspection streams only the selected database dump through the image's
`pg_restore --list`, retaining version headers. This avoids a boot-disk temporary
dump and does not touch a database. Source dump server, dump tool, selected
PostgreSQL server and restore-client majors must match. A PostgreSQL upgrade or
legacy SQL/gzip dump needs a separate reviewed procedure; this workflow does not
silently combine recovery with a major upgrade. Other extension/schema failures
remain restore failures, not evidence of compatibility.

## Preview and run

Run as the deployment account from the pinned application checkout. Infrastructure
first runs `prepare-host-storage` as root with the deployment UID/GID, then
`storage-preflight` as that account. The host needs Python 3, Make, OpenSSL and
gettext, along with the shared Docker/Compose runtime. Generated secrets remain
on the target; existing external-integration secrets are not imported from the
backup. An existing mismatching `config.mk` requires explicit reconciliation.

```sh
python3 deploy/scripts/provision-from-seed \
  --seed /absolute/path/seed.json \
  --release <exact-checked-out-commit> \
  --environment staging \
  --target-id <infrastructure-attested-instance-id> \
  --state-dir /absolute/path/to/execution-records \
  --sudo-docker
```

Default is read-only preview; it creates no execution record and starts nothing.
It checks an existing execution record against the selected identities, reports
phase status and rejects mismatched or malformed state before any apply step.
`--environment prod` selects the application's production Compose baseline but
retains the operator-only recovery profile. It does not authorize a production
operation or make the profile suitable for public service.

Add `--apply --phase <name>` to run one phase:

1. `configure`: Generate fresh missing application secrets, render Compose and
   validate the combined operator-only configuration.
2. `build`: Build the server and frontend from this release, run the frontend
   asset build as a one-off container and record image IDs. Build dependencies
   are not frozen merely by pinning Git.
3. `inspect`: Pull the release-selected data-service images, record versions and
   image IDs/digests, check exact seed identity and inspect dump compatibility.
4. `restore`: Require `--confirm-target <same-target-id>`, recheck image/seed
   identities, start only the data services, and invoke existing `inv borg.restore`
   with the explicit archive and `--force`. That command verifies archive data,
   extracts on `/shared`, restores the database, applies migrations and restores
   library/media/repository files. It is destructive to this target.
5. `prepare`: Run the same `inv prepare` task as normal deployment to collect static
   assets and rebuild search indexes from the restored database. This starts no
   web server, workers or cron and does not repeat restoration.
6. `validate`: Run Django checks, require no outstanding migrations, query the
   database and check restored content directories/sample readability. Re-running
   this phase repeats checks instead of accepting an old validation marker.

`--phase all` runs the sequence and needs the same explicit restoration target
confirmation. Completed phases resume against the same identities; mismatched
seed, release, filesystem or inspected images stop execution. A failed/interrupted
restore is never automatically repeated: add `--retry-restore` only after inspecting
partial state and renewing target confirmation. Retry can overwrite target data
and previous-file recovery directories. A host-level advisory lock serializes this
workflow; the existing application backup lock still protects actual restoration.
Other container users and operators must respect the exclusive window too.

Every one-off container bypasses image init, disables stdin/TTY and uses the
operator-only settings. Cron and the Huey consumer never start; Huey immediate
execution remains false. Mail uses the in-memory backend, Sentry is disabled
before initialization, DataCite uses dry-run and integration credentials are
disabled. Nginx is held behind a profile and loopback-only binding. These controls
do not sandbox arbitrary application code or restrict host egress.

## Evidence and activation

`<state-dir>/execution.json` associates seed, release, environment, target,
filesystem and Compose project with phase outcomes, UTC timestamps, durations,
runtime versions/image identities and validation results. It contains no secret
values. The rendered Compose configuration and `.env` can contain secrets and
must remain protected separately. Do not export them as evidence.

The final automated outcome is `basic-validation-passed-activation-held`.
Representative browser/API and published-artifact checks, extension-specific
checks and any required scientific-data acceptance remain operator functional
acceptance. `functional_attestation` remains false; this script never declares a
full recovery drill passed or updates infrastructure's recovery checkpoint.

There is deliberately no automatic activation command. Enable intended ingress,
workers, schedules and integrations only under a separately reviewed operational
step after acceptance. A drill keeps those controls held. Infrastructure exports
the execution receipt and functional acceptance alongside snapshot/volume evidence
before deleting the ephemeral host or target.

## Operator-only web acceptance using the normal deployment stack

Use nginx and the selected release's `/etc/service/django/run` uWSGI entrypoint
for HTTP acceptance. `runserver` cannot implement the application's
`X-Accel-Redirect` download handoff and is not a download validation route.
The normal `inv prepare` task must complete after restore before checking search.
`make prepare` exposes that task separately. Web startup below uses existing
images and explicitly starts only server and nginx.

Render a configuration layer on top of the ordinary generated Compose file and
`recovery.yml`:

```sh
python3 deploy/scripts/render-recovery-web --environment staging \
  --output-dir /absolute/operator/web \
  --runtime-dir /absolute/target/web
```

When rendering on the target, use the same directory for both arguments. Transfer
all generated files if rendering on the operator workstation. The renderer derives
nginx configuration from the normal staging/production configuration; it removes
PROXY protocol from the listener because the operator tunnel bypasses the edge,
and uses HTTP in uWSGI parameters. It retains the normal socket, static/media
mounts, `internal` library location and authorization handoff. `sources.json`
records the original configuration hashes. Keep this layer outside the checkout,
retain its hashes with drill evidence, and do not claim it was part of an older
application pin. Existing differing output is refused rather than overwritten.

Review the merged configuration before starting anything. Use the recorded Compose
project, `-f docker-compose.yml -f recovery.yml -f /absolute/target/web/compose.json
--profile recovery-http` for every Compose command. Confirm recovery settings,
nginx port `127.0.0.1:8080`, and the normal uWSGI entrypoint, then pull nginx and run
`run --rm --no-deps --interactive=false --no-tty --entrypoint nginx nginx -t`.
After explicit operator approval, stop the temporary web test container if one
exists and run `up -d --no-deps --no-build --pull never server nginx`.
This is the same Compose web stack and uWSGI/nginx application configuration as
normal deployment, with the recovery safety layer retained. It is not a normal
`make deploy` invocation: workers, schedules, external integrations and public
activation remain held, and existing restored data is not replaced.

Use the operator SSH tunnel for browser checks. Require a nonempty valid published
archive and compare its hash with an independently obtained copy. Record functional
acceptance separately; browser reachability and a successful basic validation
marker do not prove downloadable artifact fidelity.
