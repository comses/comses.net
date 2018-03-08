#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

echo "Deploying comses.net"
git describe --tags >| django/release-version.txt
docker-compose build --pull
docker-compose up -d
