#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

ENVIRONMENT=${1:-"dev"}

echo "Deploying latest build of comses.net for **${ENVIRONMENT}**"
SERVICES="redis db elasticsearch"
git describe --tags >| django/release-version.txt;
docker-compose build --pull;

if [[ ${ENVIRONMENT} == "dev" ]]; then
    # don't include elasticsearch2 or nginx in dev and bring up hot-reloading js server
    SERVICES="${SERVICES} js"
else
    # start js container synchronously in staging + prod and wait
    # for the compiled webpack assets to be available
    docker-compose pull db redis nginx;
    docker-compose up js;
    SERVICES="${SERVICES} elasticsearch2"
fi

docker-compose up -d cms ${SERVICES};
docker-compose exec cms inv prepare;
