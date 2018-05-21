#!/bin/bash

cd /code;
inv db.pgpass prepare;
uwsgi --ini /code/deploy/uwsgi.ini;
