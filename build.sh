#!/usr/bin/env bash

# invoke via `DEPLOY=prod ./build.sh`

set -o errexit
set -o pipefail
set -o nounset

export LC_CTYPE=C

# Adapted from http://lukeswart.net/2016/03/lets-deploy-part-1/

function clean()
{
    cat "${CONFIG_INI}"; 
    cp "${CONFIG_INI}" "${BACKUP_CONFIG_INI}";
    echo "Deleting all docker data in ./docker/shared/"
    sudo rm -rf ./docker/shared;
}

DEPLOY=${DEPLOY:-"dev"} # allowed values: (dev | staging | prod)
DEFAULT_COMPOSE_TEMPLATE="dc-${DEPLOY}.yml"
DOCKER_COMPOSE_TEMPLATE=${1:-$DEFAULT_COMPOSE_TEMPLATE}
CONFIG_INI=./deploy/conf/config.ini
BACKUP_CONFIG_INI=/tmp/comsesnet.${RANDOM}.ini

echo "Templating ${DOCKER_COMPOSE_TEMPLATE}"
echo "For improved security, consider creating a local 'comses' user with uid/gid of 2718, otherwise you'll need to run root inside the container."

set -a
. ./deploy/conf/docker.env
cp ./deploy/conf/docker.env .env

if [[ -f "${CONFIG_INI}" ]]; then
    echo "Existing ${CONFIG_INI} will be overwritten and all existing containerized data will be removed. Continue?"
    select response in "Yes" "No"; do
        case "${response}" in
            Yes) echo "Copying existing config.ini to ${BACKUP_CONFIG_INI} and then overwriting"; clean; break;;
            No) echo "Aborting build."; exit;;
        esac
    done
fi
DB_PASSWORD=$(head /dev/urandom | tr -dc '[:alnum:]' | head -c42)
DJANGO_SECRET_KEY=$(head /dev/urandom | base64 | head -c60)
TEST_BASIC_AUTH_PASSWORD=$(head /dev/urandom | tr -dc '[:alnum:]' | head -c42)
TEST_USER_ID=10000000
TEST_USERNAME=__test_user__

echo "Running env substitution for DB_PASSWORD ${DB_PASSWORD} and DJANGO_SECRET_KEY ${DJANGO_SECRET_KEY}"

cat "${CONFIG_INI}".template | envsubst > "${CONFIG_INI}"
cat "${DOCKER_COMPOSE_TEMPLATE}" | envsubst > generated-"${DOCKER_COMPOSE_TEMPLATE}"
ln -sf generated-"${DOCKER_COMPOSE_TEMPLATE}" docker-compose.yml

# Templating for integration testing frontend and backend

TEST_FRONTEND_COMMON="frontend/src/__config__/common.ts"

echo "Templating test password for JS: ${TEST_FRONTEND_COMMON}"
cat "${TEST_FRONTEND_COMMON}.template" | envsubst > "${TEST_FRONTEND_COMMON}"

docker-compose build --pull --force-rm --no-cache
