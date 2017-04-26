#!/bin/sh

/code/manage.py collectstatic --noinput --clear
uwsgi --ini /code/deploy/uwsgi.ini
