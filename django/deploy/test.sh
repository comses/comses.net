#!/bin/sh

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    /code/deploy/wait-for-it.sh db:5432 -- invoke db.init --clean
}
initdb
/code/deploy/wait-for-it.sh elasticsearch:9200 -t 30 -- invoke test --tests="$@" --coverage
