#!/bin/bash

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"core.settings.prod"}
exec uwsgi --ini /code/deploy/uwsgi.ini
