#!/bin/sh

cd /code;
inv pgpass;
/code/manage.py collectstatic --noinput --clear
uwsgi --ini /code/deploy/uwsgi.ini
