#!/bin/sh

/bin/sh /code/deploy/docker/common.sh
cd /code
python manage.py collectstatic --noinput --clear
chmod a+x /etc/periodic/daily/*
/code/deploy/docker/wait-for-it.sh solr:8983 -- python manage.py rebuild_index --noinput
crond -L /catalog/logs/crond.log
uwsgi --ini /code/deploy/uwsgi/catalog.ini
