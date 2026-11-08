#!/usr/bin/env bash
# Shared by Make, storage preparation, validation and deployment inspection.
# When sourced, this file defines values only; it never touches storage.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ "${1:-}" == --compose-files ]]; then
        DEPLOY_ENVIRONMENT=${2:-dev}
    else
        DEPLOY_ENVIRONMENT=${3:-${DEPLOY_ENVIRONMENT:-dev}}
    fi
    if [[ -n "${4:-}" ]]; then COMSES_APP_ROOT=$4; fi
fi
DEPLOY_ENVIRONMENT=${DEPLOY_ENVIRONMENT:-dev}
case "$DEPLOY_ENVIRONMENT" in
    staging|prod) DEFAULT_APP_ROOT=/srv/apps/comses; DEFAULT_LOG_ROOT=/srv/logs/comses ;;
    *) DEFAULT_APP_ROOT=$(pwd -P); DEFAULT_LOG_ROOT= ;;
esac
APP_ROOT=${COMSES_APP_ROOT:-$DEFAULT_APP_ROOT}
SHARED_ROOT=${COMSES_SHARED_ROOT:-$APP_ROOT/docker/shared}
POSTGRES_ROOT=${COMSES_POSTGRES_ROOT:-$APP_ROOT/docker/pgdata}
LOG_ROOT=${COMSES_LOG_ROOT:-${DEFAULT_LOG_ROOT:-$SHARED_ROOT/logs}}
BACKUPS_ROOT=${COMSES_BACKUPS_ROOT:-/srv/backups/comses}
SECRETS_ROOT=${COMSES_SECRETS_ROOT:-$APP_ROOT/docker/secrets}
DEPLOY_UID=${DEPLOY_UID:-1000}
DEPLOY_GID=${DEPLOY_GID:-1000}
APP_UID=${APP_UID:-0}
APP_GID=${APP_GID:-0}
POSTGRES_UID=${POSTGRES_UID:-999}
POSTGRES_GID=${POSTGRES_GID:-999}
REDIS_UID=${REDIS_UID:-999}
REDIS_GID=${REDIS_GID:-1000}
ELASTICSEARCH_UID=${ELASTICSEARCH_UID:-1000}
ELASTICSEARCH_GID=${ELASTICSEARCH_GID:-0}
NGINX_UID=${NGINX_UID:-101}
NGINX_GID=${NGINX_GID:-101}

# Pinned host paths. Overridable so storage tests can exercise the same
# staging/prod validation logic against a disposable fixture tree.
EXPECTED_APP_ROOT=${COMSES_EXPECTED_APP_ROOT:-/srv/apps/comses}
EXPECTED_SHARED_ROOT=${COMSES_EXPECTED_SHARED_ROOT:-$EXPECTED_APP_ROOT/docker/shared}
EXPECTED_POSTGRES_ROOT=${COMSES_EXPECTED_POSTGRES_ROOT:-$EXPECTED_APP_ROOT/docker/pgdata}
EXPECTED_LOG_ROOT=${COMSES_EXPECTED_LOG_ROOT:-/srv/logs/comses}
EXPECTED_BACKUPS_ROOT=${COMSES_EXPECTED_BACKUPS_ROOT:-/srv/backups/comses}
EXPECTED_SECRETS_ROOT=${COMSES_EXPECTED_SECRETS_ROOT:-$EXPECTED_APP_ROOT/docker/secrets}
SRV_ROOT=${COMSES_SRV_ROOT:-/srv}

case "$DEPLOY_ENVIRONMENT" in
    prod) COMPOSE_FILES=(base.yml staging.yml prod.yml) ;;
    staging|dev|test) COMPOSE_FILES=(base.yml "$DEPLOY_ENVIRONMENT.yml") ;;
    *) COMPOSE_FILES=() ;;
esac

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    case "${1:-}" in
        --compose-files)
            [[ ${#COMPOSE_FILES[@]} -gt 0 ]] || exit 2
            printf '%s\n' "${COMPOSE_FILES[*]}" ;;
        --get)
            case "${2:-}" in
                APP_ROOT|SHARED_ROOT|POSTGRES_ROOT|LOG_ROOT|BACKUPS_ROOT|SECRETS_ROOT) printf '%s\n' "${!2}" ;;
                *) echo 'unknown storage root' >&2; exit 2 ;;
            esac ;;
        --json)
            python3 - "$APP_ROOT" "$SHARED_ROOT" "$POSTGRES_ROOT" "$LOG_ROOT" "$BACKUPS_ROOT" "$SECRETS_ROOT" "${COMPOSE_FILES[@]}" <<'JSON'
import json, sys
layout = dict(zip(("app", "shared", "postgres", "logs", "backups", "secrets"), sys.argv[1:7]))
layout["compose_files"] = sys.argv[7:]
print(json.dumps(layout))
JSON
            ;;
        *) echo 'usage: storage-layout.sh --get ROOT [environment [app-root]] | --json | --compose-files ENVIRONMENT' >&2; exit 2 ;;
    esac
fi
