#!/usr/bin/env bash
# Shared assertions and fixture helpers for the deploy/scripts storage tests.
# Intended to be sourced, not executed directly.

TESTS_RUN=0
TESTS_FAILED=0

pass() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "ok - $1"
}

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "not ok - $1"
}

# assert_success <description> -- <command...>
assert_success() {
    local description=$1
    shift
    [ "$1" = -- ] && shift
    if "$@" >/tmp/storage-test-output.$$ 2>&1; then
        pass "$description"
    else
        fail "$description"
        sed 's/^/    /' /tmp/storage-test-output.$$
    fi
    rm -f /tmp/storage-test-output.$$
}

# assert_failure <description> -- <command...>
assert_failure() {
    local description=$1
    shift
    [ "$1" = -- ] && shift
    if "$@" >/tmp/storage-test-output.$$ 2>&1; then
        fail "$description (expected failure but command succeeded)"
        sed 's/^/    /' /tmp/storage-test-output.$$
    else
        pass "$description"
    fi
    rm -f /tmp/storage-test-output.$$
}

report_and_exit() {
    echo "---"
    echo "$TESTS_RUN tests, $TESTS_FAILED failed"
    [ "$TESTS_FAILED" -eq 0 ]
}

# make_fixture_root creates a disposable staging-like tree under $TMPDIR and
# echoes its path. Callers are responsible for sudo-owned cleanup.
make_fixture_root() {
    mktemp -d "${TMPDIR:-/tmp}/comses-storage-test.XXXXXX"
}

# fake_findmnt_bin creates a stub `findmnt` on PATH that reports any path
# under $1 as living on a non-root Cinder-backed filesystem, and otherwise
# delegates to the real findmnt.
fake_findmnt_bin() {
    local fixture_root=$1 bin_dir fixture
    bin_dir=$(mktemp -d "${TMPDIR:-/tmp}/comses-storage-test-bin.XXXXXX")
    fixture="$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fixtures/findmnt"
    cp "$fixture" "$bin_dir/findmnt"
    printf '%s\n' "$fixture_root" >"$bin_dir/findmnt.root"
    chmod +x "$bin_dir/findmnt"
    echo "$bin_dir"
}
