#!/bin/sh

CLEAN_DATABASE=${CLEAN_DATABASE:-true}
DJANGO_SETTINGS_MODULE="core.settings.dev"

chmod a+x /code/deploy/*.sh
if [ "$CLEAN_DATABASE" = true ]; then
    echo "Destroying and initializing database from scratch"
    /code/deploy/wait-for-it.sh db:5432 -- invoke initialize_database_schema --clean
else
    echo "Using existing db schema"
    /code/deploy/wait-for-it.sh db:5432 -- invoke initialize_database_schema
fi
/code/deploy/wait-for-it.sh elasticsearch:9300 -- /code/manage.py update_index
nohup /code/manage.py runserver 0.0.0.0:8000
