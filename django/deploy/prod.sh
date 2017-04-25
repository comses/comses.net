#!/bin/sh

/code/manage.py collectstatic --noinput --clear
/code/deploy/wait-for-it.sh elasticsearch:9300 -- python manage.py update_index
uwsgi --ini /code/deploy/uwsgi.ini
