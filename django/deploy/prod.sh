#!/bin/sh

cd /code;
inv db.pgpass;
/code/manage.py collectstatic --noinput --clear
uwsgi --ini /code/deploy/uwsgi.ini
