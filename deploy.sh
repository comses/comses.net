#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

ENVIRONMENT=${1:-"staging"}

echo "Deploying latest build of comses.net"
git describe --tags >| django/release-version.txt;
docker-compose build --pull;
docker-compose pull redis db nginx elasticsearch;
docker-compose up -d cms db nginx redis elasticsearch;
if [[ ${ENVIRONMENT} == "prod" ]]; then
    exec docker-compose up -d elasticsearch2
fi

docker-compose up js
docker-compose exec cms inv prepare
