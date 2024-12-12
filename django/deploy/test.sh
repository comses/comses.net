#!/bin/sh

export DJANGO_SETTINGS_MODULE="core.settings.test"

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    invoke db.init
}
initdb
exec invoke prepare test --tests="$@" --coverage
