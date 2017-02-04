#!/bin/bash

# Adapted from http://lukeswart.net/2016/03/lets-deploy-part-1/

DEPLOY=dev # or prod
DEFAULT_COMPOSE_TEMPLATE="dc-${DEPLOY}.yml"
DOCKER_COMPOSE_TEMPLATE=${1:-$DEFAULT_COMPOSE_TEMPLATE}
CONFIG_INI=deploy/conf/config.ini
BACKUP_CONFIG_INI=/tmp/comsesnet.$RANDOM.ini

echo "Templating ${DOCKER_COMPOSE_TEMPLATE}"
echo "For improved security, you should have a 'comses' user with uid/gid of 2718, otherwise you'll need to run root inside the container."

set -a
. deploy/conf/docker.env

if [[ -f "$CONFIG_INI" ]]; then
    echo "Existing $CONFIG_INI will be overwritten and you may lose access to existing containerized data. Continue?"
    select response in "Yes" "No"; do
        case "$response" in
            Yes) echo "Copying existing config.ini to $BACKUP_CONFIG_INI and then overwriting"; cat "$CONFIG_INI"; cp "$CONFIG_INI" "$BACKUP_CONFIG_INI"; break;;
            No) echo "Aborting build."; exit;;
        esac
    done
fi
DB_PASSWORD=`head /dev/urandom | tr -dc A-Za-z0-9 | head -c30`
DJANGO_SECRET_KEY=`head /dev/urandom | tr -dc A-Za-z0-9 | head -c42`

cat "$CONFIG_INI".template | envsubst > "$CONFIG_INI"
cat "${DOCKER_COMPOSE_TEMPLATE}" | envsubst > generated-"$DOCKER_COMPOSE_TEMPLATE"
ln -sf generated-"$DOCKER_COMPOSE_TEMPLATE" docker-compose.yml
docker-compose build --pull --force-rm
