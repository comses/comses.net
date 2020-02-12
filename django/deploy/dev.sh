#!/bin/bash

CLEAN_DATABASE=${CLEAN_DATABASE:-"false"}
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"core.settings.dev"}

chmod a+x /code/deploy/*.sh

initdb() {
    cd /code;
    if [ "$CLEAN_DATABASE" = "true" ]; then
        echo "Destroying and initializing database from scratch"
        /code/deploy/wait-for-it.sh db:5432 -- invoke db.init --clean
    else
        echo "Using existing db schema"
        /code/deploy/wait-for-it.sh db:5432 -- invoke db.init
    fi
}
initdb
exec /code/manage.py runserver 0.0.0.0:8000
