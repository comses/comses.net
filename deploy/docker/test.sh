#!/bin/sh

echo "running coveralls? ${RUN_COVERALLS:-false}"

/bin/sh /code/deploy/docker/common.sh
/code/deploy/docker/wait-for-it.sh db:5432 -- invoke initialize_database_schema
if [[ $RUN_COVERALLS ]]; then
    /code/deploy/docker/wait-for-it.sh solr:8983 -- invoke coverage && coveralls
else
    /code/deploy/docker/wait-for-it.sh solr:8983 -- invoke coverage
fi
