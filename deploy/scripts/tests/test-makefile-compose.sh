#!/usr/bin/env bash
# Capture actual Makefile commands without Docker, secrets or deployed storage.
set -euo pipefail

REPO_ROOT=$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/comses-make-compose.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT

# The physical directory contains spaces and differs from the symlink basename.
PROJECT="$FIXTURE/physical checkout"
ALIAS="$FIXTURE/logical-checkout"
mkdir -p "$PROJECT/deploy/scripts" "$FIXTURE/bin" "$FIXTURE/secrets" "$FIXTURE/shared"
ln -s "$PROJECT" "$ALIAS"
cp "$REPO_ROOT/Makefile" "$PROJECT/Makefile"
touch "$PROJECT"/{config.mk,base.yml,dev.yml,staging.yml,test.yml,prod.yml}
touch "$FIXTURE/secrets"/{db_password,.pgpass,django_secret_key,download_analytics_hmac_key}
touch "$PROJECT/.env"

cat > "$FIXTURE/bin/docker" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys

with open(os.environ['COMPOSE_TEST_CAPTURE'], 'a') as stream:
    stream.write(json.dumps({
        'args': sys.argv[1:],
        'project_name': os.environ.get('COMPOSE_PROJECT_NAME'),
    }) + '\n')
if 'config' in sys.argv[1:]:
    print('services: {}')
PY
cat > "$FIXTURE/bin/git" <<'SHIM'
#!/bin/sh
printf 'fixture-revision\n'
SHIM
cat > "$FIXTURE/bin/sleep" <<'SHIM'
#!/bin/sh
exit 0
SHIM
cat > "$PROJECT/deploy/scripts/envreplace" <<'SHIM'
#!/bin/sh
exit 0
SHIM
cat > "$PROJECT/deploy/scripts/storage-preflight" <<'SHIM'
#!/bin/sh
printf '{"preflight":true}\n' >> "$COMPOSE_TEST_CAPTURE"
SHIM
chmod +x "$FIXTURE/bin/"* "$PROJECT/deploy/scripts/"*

for environment in dev test staging prod; do
    for entry in "$PROJECT" "$ALIAS"; do
        export COMPOSE_TEST_CAPTURE="$FIXTURE/capture.jsonl"
        export COMPOSE_PROJECT_NAME=existing-stack
        : > "$COMPOSE_TEST_CAPTURE"
        (
            cd "$entry"
            make --no-print-directory deploy \
                "PATH=$FIXTURE/bin:/usr/bin:/bin" \
                "DEPLOY_ENVIRONMENT=$environment" \
                "COMSES_APP_ROOT=$PROJECT" \
                "COMSES_SHARED_ROOT=$FIXTURE/shared" \
                "COMSES_POSTGRES_ROOT=$FIXTURE/pgdata" \
                "COMSES_LOG_ROOT=$FIXTURE/logs" \
                "COMSES_SECRETS_ROOT=$FIXTURE/secrets" >/dev/null
        )
        python3 - "$COMPOSE_TEST_CAPTURE" "$PROJECT" "$environment" <<'PY'
import json
import sys

capture, project, environment = sys.argv[1:]
with open(capture) as stream:
    records = [json.loads(line) for line in stream]
assert records.pop(0) == {'preflight': True}, 'preflight must precede Compose'
commands = []
for record in records:
    args = record['args']
    assert args[:3] == ['compose', '--project-directory', project], args
    assert args.count('--project-directory') == 1, args
    assert '--project-name' not in args and '-p' not in args, args
    assert record['project_name'] == 'existing-stack', record
    commands.append(args[3:])
files = ['-f', 'base.yml']
if environment == 'prod':
    files += ['-f', 'staging.yml', '-f', 'prod.yml']
else:
    files += ['-f', environment + '.yml']
expected = [files + ['config'], ['build', '--pull', '--parallel'],
            ['pull', '-q', 'db', 'redis', 'elasticsearch']]
if environment != 'dev':
    expected.append(['pull', '-q', 'nginx'])
expected += [['up', '-d', '--quiet-pull'], ['exec', 'server', 'inv', 'prepare']]
assert commands == expected, (commands, expected)
PY
    done
done

printf 'Compose uses the physical project directory throughout all deploy environments.\n'
