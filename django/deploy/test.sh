#!/bin/sh

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    exec env DJANGO_SETTINGS_MODULE="core.settings.test" invoke db.init
}
initdb
exec env DJANGO_SETTINGS_MODULE="core.settings.test" invoke prepare test --tests="$@" --coverage
