#!/usr/bin/env bash
# Focused tests for deploy/scripts/storage-preflight's collaborative-root
# and private-path validation. Requires passwordless sudo to construct
# fixtures with pinned owners (root, postgres, elasticsearch, nginx UIDs)
# and to bind-mount fixture directories; never touches real /srv or repo
# storage. Run directly or via `make test-storage-scripts`.
set -uo pipefail

SCRIPT_DIR=$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(CDPATH= cd "$SCRIPT_DIR/../../.." && pwd)
STORAGE_PREFLIGHT="$REPO_ROOT/deploy/scripts/storage-preflight"
# shellcheck source=./lib.sh
. "$SCRIPT_DIR/lib.sh"

TEST_UID=$(id -u)
TEST_GID=$(id -g)
# Simulated "operators" gid: reuse the invoking user's own primary gid so the
# probe write in validate_collaborative_root succeeds through real group
# membership, the same way a deploy user who is genuinely in "operators" can
# write to debian:operators 2775 in production.
OPERATORS_TEST_GID=$TEST_GID
DEBIAN_TEST_UID=39002

# build_fixture creates a staging-shaped fixture tree at $1 and bind-mounts
# its infra-owned collaborative roots (srv-logs, srv-backups) onto the
# corresponding checkout paths (docker/shared/{logs,backups}), mirroring the
# real /srv/logs/comses and /srv/backups/comses bind mounts.
build_fixture() {
    local root=$1
    mkdir -p "$root/docker/shared"/{library,media,redis,elasticsearch/v9/primary,elasticsearch/v9/secondary,static,tls/well-known,logs/nginx,backups/repo}
    mkdir -p "$root/docker/pgdata" "$root/docker/secrets" "$root/srv-logs" "$root/srv-backups"

    sudo chown 0:0 "$root/docker/shared"
    sudo chmod 0755 "$root/docker/shared"
    sudo chown 999:999 "$root/docker/pgdata"
    sudo chmod 0700 "$root/docker/pgdata"
    sudo chown 999:1000 "$root/docker/shared/redis"
    sudo chmod 0750 "$root/docker/shared/redis"
    sudo chown 1000:0 "$root/docker/shared/elasticsearch/v9/primary" "$root/docker/shared/elasticsearch/v9/secondary"
    sudo chmod 0750 "$root/docker/shared/elasticsearch/v9/primary" "$root/docker/shared/elasticsearch/v9/secondary"
    sudo chown 101:101 "$root/docker/shared/logs/nginx"
    sudo chmod 0750 "$root/docker/shared/logs/nginx"
    chmod 0700 "$root/docker/secrets"

    sudo chown "$DEBIAN_TEST_UID:$OPERATORS_TEST_GID" "$root/docker/shared/logs" "$root/docker/shared/backups"
    sudo chmod 2775 "$root/docker/shared/logs" "$root/docker/shared/backups"

    sudo mount --bind "$root/docker/shared/logs" "$root/srv-logs"
    sudo mount --bind "$root/docker/shared/backups" "$root/srv-backups"
}

cleanup_fixture() {
    local root=$1
    sudo umount "$root/srv-logs" >/dev/null 2>&1 || true
    sudo umount "$root/srv-backups" >/dev/null 2>&1 || true
    sudo rm -rf "$root"
}

run_preflight() {
    local root=$1 bin_dir=$2
    (
        cd "$root" &&
            PATH="$bin_dir:$PATH" \
                DEPLOY_ENVIRONMENT=staging \
                COMSES_APP_ROOT="$root" \
                COMSES_SHARED_ROOT="$root/docker/shared" \
                COMSES_POSTGRES_ROOT="$root/docker/pgdata" \
                COMSES_LOG_ROOT="$root/srv-logs" \
                COMSES_BACKUPS_ROOT="$root/srv-backups" \
                COMSES_SECRETS_ROOT="$root/docker/secrets" \
                COMSES_EXPECTED_APP_ROOT="$root" \
                COMSES_EXPECTED_LOG_ROOT="$root/srv-logs" \
                COMSES_EXPECTED_BACKUPS_ROOT="$root/srv-backups" \
                COMSES_OPERATORS_GID="$OPERATORS_TEST_GID" \
                COMSES_SRV_ROOT="$root" \
                COMSES_TEST_MISSING_SRV_MOUNT="${COMSES_TEST_MISSING_SRV_MOUNT:-0}" \
                DEPLOY_UID="$TEST_UID" \
                DEPLOY_GID="$TEST_GID" \
                "$STORAGE_PREFLIGHT"
    )
}

ROOT=$(make_fixture_root)
BIN_DIR=$(fake_findmnt_bin "$ROOT")
trap 'cleanup_fixture "$ROOT"; rm -rf "$BIN_DIR"' EXIT

build_fixture "$ROOT"

assert_success "debian:operators 2775 logs and backups pass preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"

assert_success "repeated preflight is idempotent" -- \
    run_preflight "$ROOT" "$BIN_DIR"

COMSES_TEST_MISSING_SRV_MOUNT=1
assert_failure "missing /srv mount blocks preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
unset COMSES_TEST_MISSING_SRV_MOUNT

# --- world-writable collaborative path fails closed ---
sudo chmod 2777 "$ROOT/docker/shared/backups"
assert_failure "world-writable backups root fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo chmod 2775 "$ROOT/docker/shared/backups"

# --- unexpected broad group access fails closed ---
sudo chown "$DEBIAN_TEST_UID:0" "$ROOT/docker/shared/logs"
sudo chmod 2775 "$ROOT/docker/shared/logs"
assert_failure "group-writable logs root with an unexpected group fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo chown "$DEBIAN_TEST_UID:$OPERATORS_TEST_GID" "$ROOT/docker/shared/logs"
sudo chmod 2775 "$ROOT/docker/shared/logs"

# --- symlinked collaborative root fails closed ---
sudo umount "$ROOT/srv-logs"
sudo rmdir "$ROOT/srv-logs"
sudo ln -s "$ROOT/docker/shared/logs" "$ROOT/srv-logs"
assert_failure "symlinked logs root fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo rm -f "$ROOT/srv-logs"
sudo mkdir -p "$ROOT/srv-logs"
sudo mount --bind "$ROOT/docker/shared/logs" "$ROOT/srv-logs"
assert_success "preflight passes again once the logs bind mount is restored" -- \
    run_preflight "$ROOT" "$BIN_DIR"

# --- bind target and checkout source must be the same filesystem object ---
sudo umount "$ROOT/srv-backups"
assert_failure "unbound backups root does not resolve to the checkout source" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo mount --bind "$ROOT/docker/shared/backups" "$ROOT/srv-backups"
assert_success "preflight passes again once the backups bind mount is restored" -- \
    run_preflight "$ROOT" "$BIN_DIR"

# --- private paths with incorrect owner/mode fail closed ---
sudo chown 0:0 "$ROOT/docker/pgdata"
assert_failure "postgres data directory with the wrong owner fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo chown 999:999 "$ROOT/docker/pgdata"

sudo chmod 0755 "$ROOT/docker/shared/redis"
assert_failure "redis data directory with the wrong mode fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
sudo chmod 0750 "$ROOT/docker/shared/redis"

assert_success "preflight passes again once private paths are restored" -- \
    run_preflight "$ROOT" "$BIN_DIR"

# --- legacy secret authority safeguard remains intact ---
mkdir -p "$ROOT/build/secrets"
assert_failure "legacy build/secrets without COMSES_STORAGE_AUTHORITY=new fails preflight" -- \
    run_preflight "$ROOT" "$BIN_DIR"
assert_success "legacy build/secrets with COMSES_STORAGE_AUTHORITY=new passes preflight" -- \
    env COMSES_STORAGE_AUTHORITY=new bash -c '
        cd "$1" && PATH="$2:$PATH" \
            DEPLOY_ENVIRONMENT=staging \
            COMSES_APP_ROOT="$1" \
            COMSES_SHARED_ROOT="$1/docker/shared" \
            COMSES_POSTGRES_ROOT="$1/docker/pgdata" \
            COMSES_LOG_ROOT="$1/srv-logs" \
            COMSES_BACKUPS_ROOT="$1/srv-backups" \
            COMSES_SECRETS_ROOT="$1/docker/secrets" \
            COMSES_EXPECTED_APP_ROOT="$1" \
            COMSES_EXPECTED_LOG_ROOT="$1/srv-logs" \
            COMSES_EXPECTED_BACKUPS_ROOT="$1/srv-backups" \
            COMSES_OPERATORS_GID="'"$OPERATORS_TEST_GID"'" \
            COMSES_SRV_ROOT="$1" \
            DEPLOY_UID="'"$TEST_UID"'" \
            DEPLOY_GID="'"$TEST_GID"'" \
            "'"$STORAGE_PREFLIGHT"'"
    ' _ "$ROOT" "$BIN_DIR"
rm -rf "$ROOT/build"

report_and_exit
