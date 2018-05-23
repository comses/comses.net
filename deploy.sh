#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Deploying latest build of comses.net"
git describe --tags >| django/release-version.txt
docker-compose build --pull
docker-compose pull redis db nginx
docker-compose up -d cms
docker-compose up js
docker-compose exec cms inv prepare
