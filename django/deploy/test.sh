#!/bin/sh

chmod a+x /code/deploy/*.sh;
cd /code;
/code/deploy/wait-for-it.sh db:5432 -- invoke initialize_database_schema;
/code/deploy/wait-for-it.sh elasticsearch:9300 -- invoke test --tests="$@" --coverage
