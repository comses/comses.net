#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

ENVIRONMENT=${1:-"dev"}

echo "Deploying latest build of comses.net for **${ENVIRONMENT}**"
SERVICES="redis db elasticsearch nginx"
git describe --tags >| django/release-version.txt;
docker-compose build --pull;

if [[ ${ENVIRONMENT} == "dev" ]]; then
    SERVICES="redis db elasticsearch js"
fi

docker-compose pull ${SERVICES}

if [[ ${ENVIRONMENT} == "prod" ]]; then
    SERVICES="${SERVICES} elasticsearch2"
    docker-compose up js
fi

docker-compose up -d cms ${SERVICES};
docker-compose exec cms inv prepare
