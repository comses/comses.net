#!/usr/bin/env bash
# Focused tests for deploy/scripts/prepare-host-storage. Requires
# passwordless sudo because the script itself requires root. All fixtures
# live under a disposable mktemp tree; never touches real /srv storage.
set -uo pipefail

SCRIPT_DIR=$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(CDPATH= cd "$SCRIPT_DIR/../../.." && pwd)
PREPARE_HOST_STORAGE="$REPO_ROOT/deploy/scripts/prepare-host-storage"
# shellcheck source=./lib.sh
. "$SCRIPT_DIR/lib.sh"

run_prepare() {
    local root=$1 bin_dir=$2
    sudo env \
        PATH="$bin_dir:$PATH" \
        COMSES_APP_ROOT="$root" \
        COMSES_SHARED_ROOT="$root/docker/shared" \
        COMSES_POSTGRES_ROOT="$root/docker/pgdata" \
        COMSES_LOG_ROOT="$root/srv-logs" \
        COMSES_BACKUPS_ROOT="$root/srv-backups" \
        COMSES_SECRETS_ROOT="$root/docker/secrets" \
        COMSES_EXPECTED_APP_ROOT="$root" \
        COMSES_EXPECTED_LOG_ROOT="$root/srv-logs" \
        COMSES_EXPECTED_BACKUPS_ROOT="$root/srv-backups" \
        COMSES_SRV_ROOT="$root" \
        COMSES_TEST_MISSING_SRV_MOUNT="${COMSES_TEST_MISSING_SRV_MOUNT:-0}" \
        "${@:3}" \
        "$PREPARE_HOST_STORAGE"
}

owner_mode() {
    stat -c '%u:%g %a' "$1"
}

ROOT=$(make_fixture_root)
BIN_DIR=$(fake_findmnt_bin "$ROOT")
trap 'sudo umount "$ROOT/srv-logs" >/dev/null 2>&1; sudo umount "$ROOT/srv-backups" >/dev/null 2>&1; sudo rm -rf "$ROOT"; rm -rf "$BIN_DIR"' EXIT

mkdir -p "$ROOT/srv-logs" "$ROOT/srv-backups"
# Simulate infrastructure already having bind-mounted the canonical
# collaborative roots (debian:operators-equivalent 2775) onto the checkout
# before prepare-host-storage runs.
sudo chown 39002:0 "$ROOT/srv-logs" "$ROOT/srv-backups"
sudo chmod 2775 "$ROOT/srv-logs" "$ROOT/srv-backups"
BEFORE_LOG_ROOT=$(owner_mode "$ROOT/srv-logs")
BEFORE_BACKUPS_ROOT=$(owner_mode "$ROOT/srv-backups")

assert_success "prepare-host-storage runs on a fresh fixture" -- \
    run_prepare "$ROOT" "$BIN_DIR"

COMSES_TEST_MISSING_SRV_MOUNT=1
assert_failure "missing /srv mount blocks preparation" -- \
    run_prepare "$ROOT" "$BIN_DIR"
unset COMSES_TEST_MISSING_SRV_MOUNT

AFTER_LOG_ROOT=$(owner_mode "$ROOT/srv-logs")
AFTER_BACKUPS_ROOT=$(owner_mode "$ROOT/srv-backups")
if [ "$BEFORE_LOG_ROOT" = "$AFTER_LOG_ROOT" ] && [ "$BEFORE_BACKUPS_ROOT" = "$AFTER_BACKUPS_ROOT" ]; then
    pass "preparation does not alter infrastructure-owned logs/backups roots"
else
    fail "preparation does not alter infrastructure-owned logs/backups roots"
    echo "    logs: before=$BEFORE_LOG_ROOT after=$AFTER_LOG_ROOT"
    echo "    backups: before=$BEFORE_BACKUPS_ROOT after=$AFTER_BACKUPS_ROOT"
fi

# --- exact-mode private paths are created correctly ---
SHARED_MODE=$(owner_mode "$ROOT/docker/shared")
if [ "$SHARED_MODE" = "0:0 755" ]; then
    pass "docker/shared gets exact private owner/mode"
else
    fail "docker/shared gets exact private owner/mode (got $SHARED_MODE)"
fi

# --- stale setgid bit on a private path is cleared ---
sudo chmod 2755 "$ROOT/docker/shared"
STALE_MODE=$(stat -c '%a' "$ROOT/docker/shared")
assert_success "prepare-host-storage re-runs against a setgid-tainted private path" -- \
    run_prepare "$ROOT" "$BIN_DIR"
CLEARED_MODE=$(stat -c '%a' "$ROOT/docker/shared")
if [ "$STALE_MODE" = "2755" ] && [ "$CLEARED_MODE" = "755" ]; then
    pass "stale setgid bit on docker/shared is cleared to exactly 0755"
else
    fail "stale setgid bit on docker/shared is cleared to exactly 0755 (stale=$STALE_MODE cleared=$CLEARED_MODE)"
fi

# --- repeated preparation is idempotent ---
FIRST_RUN_STATE=$(sudo find "$ROOT/docker" "$ROOT/srv-logs" "$ROOT/srv-backups" -printf '%p %u:%g %m\n' | sort)
assert_success "prepare-host-storage runs a second time" -- \
    run_prepare "$ROOT" "$BIN_DIR"
SECOND_RUN_STATE=$(sudo find "$ROOT/docker" "$ROOT/srv-logs" "$ROOT/srv-backups" -printf '%p %u:%g %m\n' | sort)
if [ "$FIRST_RUN_STATE" = "$SECOND_RUN_STATE" ]; then
    pass "repeated preparation is idempotent"
else
    fail "repeated preparation is idempotent"
    diff <(echo "$FIRST_RUN_STATE") <(echo "$SECOND_RUN_STATE") | sed 's/^/    /'
fi

# --- legacy/new secret authority safeguard remains intact ---
sudo mkdir -p "$ROOT/build/secrets"
sudo bash -c "echo legacy > '$ROOT/build/secrets/db_password'"
sudo bash -c "echo current > '$ROOT/docker/secrets/db_password'"
assert_failure "legacy build/secrets with divergent docker/secrets blocks preparation" -- \
    run_prepare "$ROOT" "$BIN_DIR"
assert_success "COMSES_STORAGE_AUTHORITY=new allows preparation to proceed" -- \
    run_prepare "$ROOT" "$BIN_DIR" COMSES_STORAGE_AUTHORITY=new
sudo rm -rf "$ROOT/build"

report_and_exit
