#!/bin/sh

CLEAN_DATABASE=${CLEAN_DATABASE:-true}
DJANGO_SETTINGS_MODULE="core.settings.dev"

/bin/sh /code/deploy/app/common.sh
#/code/deploy/app/wait-for-it.sh elasticsearch:9200 -- python manage.py rebuild_index --noinput
if [ "$CLEAN_DATABASE" = true ]; then
    echo "Destroying and initializing database from scratch"
    /code/deploy/app/wait-for-it.sh db:5432 -- invoke initialize_database_schema --clean
else
    echo "Using existing db schema"
    /code/deploy/app/wait-for-it.sh db:5432 -- invoke initialize_database_schema
fi
exec ./manage.py runserver 0.0.0.0:8000
