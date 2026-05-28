#!/bin/sh

chmod a+x /code/deploy/*.sh;

wait_for_elasticsearch() {
    echo "Waiting for Elasticsearch to report yellow/green health"
    python - <<'PY'
import base64
import json
import sys
import time
from urllib import request

url = "http://elasticsearch:9200/_cluster/health"
auth = base64.b64encode(b"elastic:elastic").decode("ascii")
headers = {"Authorization": f"Basic {auth}"}

for attempt in range(60):
    try:
        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        status = data.get("status")
        if status in {"yellow", "green"}:
            print(f"Elasticsearch is healthy: {status}")
            sys.exit(0)
    except Exception:
        pass
    time.sleep(2)

print("Timed out waiting for Elasticsearch health", file=sys.stderr)
sys.exit(1)
PY
}

wait_for_elasticsearch

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