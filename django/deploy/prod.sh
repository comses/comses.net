#!/bin/sh

/code/manage.py collectstatic --noinput --clear
# FIXME: rebuild elasticsearch index?
# /code/deploy/wait-for-it.sh solr:8983 -- python manage.py rebuild_index --noinput
uwsgi --ini /code/deploy/uwsgi.ini
