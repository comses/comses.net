#!/bin/sh

chmod a+x /code/deploy/*.sh;
cd /code;
/code/deploy/wait-for-it.sh db:5432 -- invoke initialize_database_schema;
invoke test --tests="$@" --coverage
