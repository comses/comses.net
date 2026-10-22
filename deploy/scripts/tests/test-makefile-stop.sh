#!/usr/bin/env bash
# Focused tests for the ordered, fail-closed `make stop` workflow.
set -euo pipefail

REPO_ROOT=$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/comses-make-stop.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT

cp "$REPO_ROOT/Makefile" "$FIXTURE/Makefile"
touch "$FIXTURE"/{config.mk,base.yml,dev.yml,staging.yml,test.yml,prod.yml,docker-compose.yml}
mkdir -p "$FIXTURE/bin" "$FIXTURE/docker/secrets"
touch "$FIXTURE/docker/secrets"/{db_password,.pgpass,django_secret_key}
# Keep the included environment newer than its secret prerequisites so this
# isolated fixture does not invoke the repository's environment generator.
touch "$FIXTURE/.env"

cat >"$FIXTURE/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >>"$DOCKER_LOG"

if [[ "$*" == "compose ps --status running --services" ]]; then
    count=0
    [[ ! -f "$DOCKER_PS_COUNT" ]] || count=$(<"$DOCKER_PS_COUNT")
    count=$((count + 1))
    printf '%s\n' "$count" >"$DOCKER_PS_COUNT"
    if ((count == 1)); then
        [[ "${FAKE_REDIS_RUNNING:-1}" == 1 ]] && echo redis
    elif [[ -n "${FAKE_FINAL_RUNNING:-}" ]]; then
        echo "$FAKE_FINAL_RUNNING"
    fi
elif [[ "$*" == "compose exec -T redis redis-cli -s /data/redis.sock SAVE" ]]; then
    [[ "${FAKE_REDIS_SAVE_FAIL:-0}" != 1 ]] || exit 1
    echo "${FAKE_REDIS_SAVE_RESPONSE:-OK}"
elif [[ "$*" == "compose ps --all --quiet" ]]; then
    [[ -z "${FAKE_CONTAINER_IDS:-}" ]] || printf '%s\n' $FAKE_CONTAINER_IDS
elif [[ "${1:-}" == inspect ]]; then
    echo "/fake-container ${FAKE_EXIT_CODE:-0}"
fi
EOF
chmod +x "$FIXTURE/bin/docker"

run_stop() {
    local environment=$1 log=$2 count=$3
    shift 3
    env \
        PATH="$FIXTURE/bin:$PATH" \
        DOCKER_LOG="$log" \
        DOCKER_PS_COUNT="$count" \
        "$@" \
        make --no-print-directory -C "$FIXTURE" stop \
        "DEPLOY_ENVIRONMENT=$environment" \
        "COMSES_APP_ROOT=$FIXTURE" \
        "COMSES_SHARED_ROOT=$FIXTURE/docker/shared" \
        "COMSES_POSTGRES_ROOT=$FIXTURE/docker/pgdata" \
        "COMSES_LOG_ROOT=$FIXTURE/docker/shared/logs" \
        "COMSES_BACKUPS_ROOT=$FIXTURE/docker/shared/backups" \
        "COMSES_SECRETS_ROOT=$FIXTURE/docker/secrets"
}

assert_log() {
    local description=$1 expected=$2 actual=$3
    if diff -u "$expected" "$actual"; then
        echo "ok - $description"
    else
        echo "not ok - $description" >&2
        exit 1
    fi
}

staging_log="$FIXTURE/staging.log"
staging_count="$FIXTURE/staging.count"
run_stop staging "$staging_log" "$staging_count"
cat >"$FIXTURE/staging.expected" <<'EOF'
compose stop --timeout 120 nginx
compose stop --timeout 180 server
compose ps --status running --services
compose exec -T redis redis-cli -s /data/redis.sock SAVE
compose stop --timeout 120
compose ps --status running --services
compose ps --all --quiet
EOF
assert_log "staging stops ingress and workers before persisting Redis" "$FIXTURE/staging.expected" "$staging_log"

dev_log="$FIXTURE/dev.log"
dev_count="$FIXTURE/dev.count"
run_stop dev "$dev_log" "$dev_count"
! grep -Fq "stop --timeout 120 nginx" "$dev_log"
echo "ok - development does not require the nginx service"

stopped_log="$FIXTURE/stopped.log"
stopped_count="$FIXTURE/stopped.count"
run_stop staging "$stopped_log" "$stopped_count" FAKE_REDIS_RUNNING=0
! grep -Fq "redis-cli" "$stopped_log"
echo "ok - repeated shutdown skips Redis persistence when Redis is already stopped"

save_failure_log="$FIXTURE/save-failure.log"
save_failure_count="$FIXTURE/save-failure.count"
if run_stop staging "$save_failure_log" "$save_failure_count" FAKE_REDIS_SAVE_FAIL=1; then
    echo "not ok - Redis SAVE failure did not stop the shutdown" >&2
    exit 1
fi
! grep -Fxq "compose stop --timeout 120" "$save_failure_log"
echo "ok - Redis SAVE failure preserves stateful services"

running_log="$FIXTURE/running.log"
running_count="$FIXTURE/running.count"
if run_stop staging "$running_log" "$running_count" FAKE_FINAL_RUNNING=elasticsearch; then
    echo "not ok - remaining running service did not fail the shutdown" >&2
    exit 1
fi
echo "ok - shutdown fails when a service remains running"

forced_log="$FIXTURE/forced.log"
forced_count="$FIXTURE/forced.count"
if run_stop staging "$forced_log" "$forced_count" FAKE_CONTAINER_IDS=container-1 FAKE_EXIT_CODE=137; then
    echo "not ok - SIGKILL exit did not fail the shutdown" >&2
    exit 1
fi
echo "ok - shutdown reports containers that exceed the graceful timeout"

rm "$FIXTURE/docker-compose.yml"
missing_log="$FIXTURE/missing.log"
missing_count="$FIXTURE/missing.count"
if run_stop staging "$missing_log" "$missing_count"; then
    echo "not ok - missing rendered Compose file did not fail the shutdown" >&2
    exit 1
fi
[[ ! -s "$missing_log" ]]
echo "ok - shutdown refuses to regenerate missing Compose configuration"
