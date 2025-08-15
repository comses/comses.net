#!/bin/bash

CLEAN_DATABASE=${CLEAN_DATABASE:-"false"}
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"core.settings.dev"}

chmod a+x /code/deploy/*.sh

initdb() {
    cd /code;
    if [ "$CLEAN_DATABASE" = "true" ]; then
        echo "Destroying and initializing database from scratch"
        invoke db.init --clean
    else
        echo "Using existing db schema"
        invoke db.init
    fi
}
initdb
echo "Running dev server with ${DJANGO_SETTINGS_MODULE}"
exec env DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE} /code/manage.py runserver 0.0.0.0:8000
