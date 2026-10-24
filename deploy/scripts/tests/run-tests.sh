#!/usr/bin/env bash
# Runs the deploy/scripts storage test suites. Requires passwordless sudo;
# operates only on disposable mktemp fixtures, never real /srv storage.
set -uo pipefail

SCRIPT_DIR=$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
status=0

for test_script in "$SCRIPT_DIR"/test-*.sh; do
    echo "=== $(basename "$test_script") ==="
    bash "$test_script" || status=1
    echo
done

exit "$status"
