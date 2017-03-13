#!/bin/sh

chmod a+x /code/deploy/*.sh
cd /code
python manage.py collectstatic --noinput --clear
# set up cron
# re-index via elasticsearch instead
# /code/deploy/app/wait-for-it.sh solr:8983 -- python manage.py rebuild_index --noinput
uwsgi --ini /code/deploy/uwsgi.ini
