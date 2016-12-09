#!/bin/sh

/bin/sh /code/deploy/app/common.sh
#/code/deploy/app/wait-for-it.sh db:5432 -- invoke restore_from_dump
#/code/deploy/app/wait-for-it.sh solr:8983 -- python manage.py rebuild_index --noinput
/code/deploy/app/wait-for-it.sh db:5432 -- python manage.py runserver 0.0.0.0:8000
