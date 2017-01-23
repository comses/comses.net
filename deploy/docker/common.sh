#!/bin/sh

LOCAL_PY_TEMPLATE=${1-"/code/comses/settings/local.py.example"}
LOCAL_PY="/code/catalog/settings/local.py"
if [ ! -f $LOCAL_PY ]; then
    echo "Copying $LOCAL_PY_TEMPLATE to $LOCAL_PY"
    cp -p $LOCAL_PY_TEMPLATE $LOCAL_PY
fi
chmod +x /code/deploy/docker/*.sh
