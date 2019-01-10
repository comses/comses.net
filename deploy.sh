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
else
    # bring js container up synchronously in staging + prod
    docker-compose pull db redis nginx
    docker-compose up js
fi

if [[ ${ENVIRONMENT} == "prod" ]]; then
    SERVICES="${SERVICES} elasticsearch2"
fi

docker-compose up -d cms ${SERVICES};
docker-compose exec cms inv prepare
