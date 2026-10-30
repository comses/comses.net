# Publish and provision an explicit seed with a pinned release

This is the application side of the shared provisioning contract: publish an
identified, validated seed, restore seed X with release Y, validate it, and hold
activation for separate operator approval.
Initial staging, a production rebuild and an ephemeral drill use the same
application phases. Environment-specific credentials and infrastructure state
remain separate. Seeds use a Borg repository containing a custom-format database
dump and matching shared files. `build_synthetic_seed` constructs synthetic
candidates; minimal/sanitized seed publication follows the operator workflow
below. `provision-from-seed` consumes seeds and does not build fixtures, sanitize
production data, or publish seeds automatically.

## Responsibility boundary

| Owner | Responsibilities |
| --- | --- |
| Infrastructure repository | Cloud resources and quotas; networks; operator authority and SSH trust; verified disk identification, formatting and mounting; shared container runtime; application checkout pin; verified snapshot/clone selection; local working repository delivery; handoff and independent evidence export; ephemeral resource teardown. |
| This application release | Seed content/layout and validation requirements; existing Borg backup packaging; storage ownership/layout helpers; application prerequisites; configuration and fresh generated secrets; Compose/build/runtime requirements; seed identity and dump compatibility checks; existing Borg restore and migrations; application validation; safe application profile and activation policy. |
| Operator | Approve seed content, sanitization, audience, release and destination; publish seed evidence and authorize distribution; authorize data replacement; inspect failures and explicitly authorize destructive retries; perform functional acceptance; approve activation independently; retain evidence and close the drill. |

Infrastructure invokes this release's entry point. It must not reimplement image
selection, Compose service commands, Django settings, restore logic, migrations
or application secret generation. The application does not identify Cinder
devices, manage SSH trust, create/delete snapshots or borrow cloud credentials.
The target identity supplied to the application is an infrastructure attestation;
the application additionally binds execution to the mounted `/srv` filesystem
UUID. It does not independently authenticate a cloud instance UUID.

## Publish a minimal or sanitized seed

Seed publication means making a fixed, approved recovery input and its evidence
available to an authorized consumer. It does not mean publishing a model release,
registering a DOI, making the seed public, or enabling backup schedules. A replica
of a full backup can still be selected through the handoff below; it must not be
labelled sanitized without the content review described here.

### 1. Declare content, audience, and coverage

Record the publisher, intended consumers, source provenance, application commit,
database/tool versions, fixture-builder or sanitization-script commit, and approved
distribution location. Choose and label one of these scopes:

- **Minimal synthetic:** build a fresh database and matching files from synthetic
  fixtures using the pinned application's models/validated import paths. Include
  only approved synthetic identities and test content. This is the preferred
  option when real production content is unnecessary.
- **Sanitized subset:** select explicitly approved records and files from an
  isolated source copy, with an allowlist and a reviewed transformation/removal
  policy covering related objects and all retained storage. Record exclusions and
  preserve referential integrity. A reduced database alone is not a sanitized seed.

For recovery acceptance, include actual model source, documentation and data,
a model with at least two distinct published versions, a representative larger
archive, private fixtures, and enough public records for pagination/filter checks.
Record sizes, file counts, paths, archive and extracted-file SHA-256 hashes, and
expected search IDs/order. A documentation/metadata-only ZIP is insufficient.
An intentionally smaller bootstrap seed may be published with its coverage limits,
but cannot satisfy the missing recovery cases.

Preserve retained real published artifacts, DOI assignments and archival citation
metadata byte-for-byte where applicable. If a published object contains data that
cannot be distributed to the intended audience, exclude it and its dependencies
or substitute a separately identified synthetic fixture; never anonymize it in
place while retaining its real published identity. Synthetic publication/review
states must be created through a reviewed fixture procedure with external effects
suppressed, not by contacting live DOI or review services.

A synthetic/subset seed proves only its stated coverage and restore mechanics.
Its build timestamp is not a production recovery point, and its restore duration
does not establish production-scale recovery time. Production recovery acceptance
still requires the appropriately scoped backup and agreed timing objectives.

### 2. Build and sanitize in isolation

Use a disposable builder with its own database, shared root, Compose project and
fresh secrets. Pin the application and record image identities. Apply the recovery
profile described below before application commands: keep live mail, DOI, webhooks,
SSO redirects, workers, schedules and public ingress suppressed. Infrastructure
must supply any required network isolation; recovery settings alone do not block
host egress. Never sanitize the production database, source backup or published
source files.

Run the versioned fixture/import/sanitization procedure and retain its report.
There is no generic sanitizer in `provision-from-seed`; an absent or unreviewed
procedure blocks sanitized publication. Review the retained database and files
for real account emails/profile data, password hashes, sessions, reset/API/SSO
tokens, share capabilities, private reviews/messages, and embedded credentials or
personal data in uploads, archives, repository history and metadata. Remove or
replace these only according to the approved policy. Seed accounts must have no
usable shared credentials; create any test login locally after restore.

Materialize only approved library/media/artifact-repository contents. Reconcile
database references against that file inventory and verify expected hashes.
Do not carry source logs, caches, previous restore trees, configuration secrets,
old dumps or old Borg archives into the distributable seed. Keep the original
source restricted even when the resulting seed is approved for wider access.

### Automated synthetic candidate builder

The `build_synthetic_seed` management command and `core.synthetic_seed` own the
`synthetic-v1` fixture policy. There is no production-data input or sanitization
mode. Infrastructure must supply an **empty, already created PostgreSQL database**
on a separate disposable PostgreSQL instance, isolated mounts and fresh configuration.
Use the intended restore database name (normally `comsesnet`): the existing restore
contract locates the dump by that name. The command refuses system databases and
any existing application tables, views or sequences, including other schemas.
Do not use `inv db.init`: the builder applies migrations itself and refuses any
database that already has tables. It also refuses existing fixture storage.

Use a pinned checkout/image and the recovery Compose override. Set `SEED_PROJECT`
to the disposable project and `SEED_RELEASE` to the full application commit that
infrastructure has verified; the report records this as a caller attestation,
not an independent Git/image verification. Example read-only preflight:

```bash
docker compose --project-name "$SEED_PROJECT" \
  -f docker-compose.yml -f recovery.yml \
  run --rm --no-deps --interactive=false --no-tty \
  -e DJANGO_SETTINGS_MODULE=core.settings.seed \
  -e COMSES_SEED_DATABASE=comsesnet \
  -e COMSES_SEED_ROOT=/shared/seeds/candidate01 \
  --entrypoint python server /code/manage.py build_synthetic_seed \
  --confirm-database comsesnet \
  --confirm-root /shared/seeds/candidate01 --release "$SEED_RELEASE"
```

Add `--apply` to create the schema and fixtures. A database advisory lock serializes
builders; an exclusively created report claims the storage root. Keep all other
writers stopped. An interrupted/failed candidate must be investigated and rebuilt
in a **new empty database/root**; there is no destructive automatic retry/cleanup.

The seed settings inherit integration suppression from recovery, disable automatic
search indexing, and keep deferred Huey work in process-local memory without
executing it or sending it to Redis. The builder uses the existing release
publication validation and archive generation synchronously. It creates twelve
public codebases, two versions of one model, a private codebase, Unicode authors,
source/docs/data, and a larger deterministic CSV (8 MiB by default;
`--large-data-mib` accepts 1–64). The two synthetic accounts and the framework
anonymous identity are inactive with unusable passwords; releases have no share
capabilities or assigned DOIs.

`<seed-root>/seed-build.json` records status, policy and builder identity, release
IDs/paths, archive and storage hashes, coverage and limitations. `built-unapproved`
means the fixtures and archives passed local construction checks. It does **not**
mean restored HTTP permissions, search, schema conformance, production-scale timing,
publication approval or recovery acceptance passed. Review the declared larger
fixture size for representativeness. Create test logins only on a restored drill
target; do not add usable credentials to the distributable candidate.

For the packaging commands below, pass the **same** `DJANGO_SETTINGS_MODULE`,
`COMSES_SEED_DATABASE` and `COMSES_SEED_ROOT` using `run -e` on every invocation.
The seed profile maps Borg/dump/library/media/repository paths beneath that seed
root; omitting it would select the ordinary application database/storage instead.
The success marker is then at `/shared/seeds/candidate01/backups/last-successful-backup`.
Export the report independently; it is intentionally outside the archived content
directories. Packaging, restore testing and operator approval remain required.

### 3. Package a fixed candidate with existing backup tooling

Stop every writer to the builder, including web processes and fixture jobs, while
leaving its database available. The backup lock serializes backup operations;
it does not prevent application uploads. Verify the builder's backup staging
directory contains no inherited dumps and its Borg repository path does not yet
exist. Initialize a **fresh repository**, never a copy of a production repository:
older archives/chunks can otherwise retain excluded information. Do not delete
archives or compact the source to manufacture a sanitized repository.

Use the already reviewed builder Compose configuration and recovery override,
with the same project and environment selector throughout. For example, after
setting `SEED_PROJECT` to the verified disposable project name:

```bash
seed_compose=(docker compose --project-name "$SEED_PROJECT"
  -f docker-compose.yml -f recovery.yml)
"${seed_compose[@]}" run --rm --no-deps --interactive=false --no-tty \
  --entrypoint inv server borg.init
"${seed_compose[@]}" run --rm --no-deps --interactive=false --no-tty \
  --entrypoint inv server borg.backup-all
"${seed_compose[@]}" run --rm --no-deps --interactive=false --no-tty \
  --entrypoint cat server /shared/backups/last-successful-backup
```

These commands require an already configured builder and running database; they
are not a builder setup script. Confirm effective mounts/settings before running.
The existing task produces a fresh validated custom-format dump, archives the
library, media, artifact repository and `backups/latest`, verifies archive data,
and writes the local success marker. See the [backup runbook](backup-restore-runbook.md)
for its implementation contract. `borg.init` currently uses `--encryption=none`;
the seed is not encrypted by Borg, so infrastructure must enforce appropriate
storage/transport protection and audience access.

Record the exact archive name from that successful run. Collect repository ID,
archive fingerprint, file inventory and verification results using the pinned
Borg runtime, and populate the unchanged handoff manifest below. Freeze the
candidate repository; do not add further archives during review. Transfer only
this repository and approved non-secret manifests/evidence, not the builder's
entire shared root, `.env`, generated Compose secrets or credentials. If packaging
the repository for transport, record the package SHA-256 and verify it after
transfer; a transport hash does not replace Borg integrity or content review.

### 4. Restore-test, approve, and publish

Deliver a working copy of the exact candidate to a second disposable target and
run the preview/apply/validation and operator-only HTTP procedures below. Verify
the source fixture hashes against restored downloads through nginx, database/file
reconciliation, schema/citation fidelity, public/private search results, and direct
private-file/share-link/cache isolation. Inspect the restored database and retained
files for the excluded sensitive data as well as checking application access.
A successful backup marker or an HTTP 200 alone cannot approve publication.

Apply the [functional test plan's recovery acceptance criteria](https://github.com/comses/planning/wiki/comses-functional-test-plan#10-recovery-acceptance--isolated-restore-target)
within the declared seed scope. Retain the seed identity, provenance, content and
sanitization policy/report, coverage and exclusions, fixture hashes, runtime pins,
restore receipt, test failures/reruns and results in an access-controlled evidence
location independent of both builder and restore target. Verify retrieval there.
Do not export raw sensitive findings into a broadly accessible evidence bundle.

The publisher and approving operator record approval of the **exact** repository
ID/archive fingerprint and audience. Infrastructure then promotes that fixed
candidate to its protected distribution location, verifies the delivered identity,
and publishes the handoff manifest with its independent `evidence_ref`. Consumers
must not select an unapproved candidate or a mutable “latest” alias. Keep publication
approval separate from later target recovery acceptance and schedule activation.

Failed review leaves the candidate unpublished. Correct the fixture/sanitization
procedure and create a new candidate identity; do not overwrite an approved seed.
Retain prior failure evidence. After independent evidence export, clean up the
disposable builder/restore target and revoke temporary access, verifying cleanup
without deleting the approved seed or evidence. Revocation of a previously
approved seed must be recorded for consumers rather than silently replacing it.

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

With `--sudo-docker`, the workflow passes the non-secret recovery environment
selector explicitly across sudo; inheriting the caller environment is insufficient
because sudo normally clears it. For direct Compose commands outside the workflow,
set `COMSES_PROVISION_ENVIRONMENT=prod` in the production recovery checkout's local
`.env`, and verify the effective server environment before running application
commands. Keep `DJANGO_SETTINGS_MODULE=core.settings.recovery`.

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

### External authentication: alternate access path

**Security hazard:** a restored database can restore a usable external
authentication path. Allauth `SocialApp` records can supply provider credentials,
and `SocialAccount` records retain links between external identities and local
users. Clearing environment secrets or changing a local password does not, by
itself, disable that path. If the provider flow succeeds, a linked external
identity can authenticate to the restored application under the application's
account policy. An operator-only tunnel limits reachability; it does not disable
authentication for someone who can reach it.

The explicit Django setting `EXTERNAL_AUTH_ENABLED` controls both backend
enforcement and the social-login buttons:

| Settings profile | Value | Behavior |
| --- | --- | --- |
| Normal development, test, staging and production | `True` | External authentication is available subject to provider configuration and account permissions. |
| Recovery (and profiles inheriting recovery) | `False` | External-auth views return 403 before executing; local password login remains available. |

`core.external_auth.ExternalAuthMiddleware` is installed in the common middleware
list. Only the Boolean `True` enables external authentication; this is a Django
settings policy, not an automatically read environment variable. Keep it false
throughout a drill. The guard blocks allauth social login, account linking,
connection management and callbacks, plus Discourse and Librarian SSO handoffs.
It leaves restored provider/account records intact. Hiding buttons alone is not
the security control, and empty provider secrets are not proof of disablement.

Verify GitHub/ORCID initiation and callback URLs return 403 without a `Location`
header while local login/logout still work. Do not follow live identity-provider
redirects during the test. Before enabling external authentication on a rebuilt
service, review the restored providers, linked accounts, callback destinations
and intended audience as part of the separate activation decision. Never export
provider credentials as evidence.

This control does not revoke existing authenticated sessions, invalidate upstream
tokens, disable local accounts, or restrict host egress. Where access revocation
is required, handle those separately; do not describe this flag as a complete
account lockdown.

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
