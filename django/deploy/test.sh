#!/bin/sh

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    env DJANGO_SETTINGS_MODULE="core.settings.test" invoke db.init
}
initdb

if [ "$#" -gt 0 ]; then
    TEST_SELECTOR="$*"
    exec env DJANGO_SETTINGS_MODULE="core.settings.test" invoke collectstatic test --tests="$TEST_SELECTOR" --coverage
fi

exec env DJANGO_SETTINGS_MODULE="core.settings.test" invoke collectstatic test --coverage