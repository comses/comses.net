#!/usr/bin/env bash

# Adapted from http://lukeswart.net/2016/03/lets-deploy-part-1/

DOCKER_COMPOSE_TEMPLATE=${1:-development.yml}

echo "templating ${DOCKER_COMPOSE_TEMPLATE}"

set -a
. deploy/conf/docker.env

DB_PASSWORD=`head /dev/urandom | tr -dc A-Za-z0-9 | head -c30`
DJANGO_SECRET_KEY=`head /dev/urandom | tr -dc A-Za-z0-9 | head -c42`

cat deploy/conf/config.ini.template | envsubst > deploy/conf/config.ini
cat ${DOCKER_COMPOSE_TEMPLATE} | envsubst > docker-compose.yml
docker-compose build
