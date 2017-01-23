#!/bin/sh

/code/deploy/docker/wait-for-it.sh db:5432 -- invoke restore_from_dump
python manage.py runserver 0.0.0.0:8000
