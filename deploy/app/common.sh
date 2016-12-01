#!/bin/sh

LOCAL_PY_TEMPLATE=${1-"/code/wagtail_comses_net/settings/local.py.example"}
LOCAL_PY="/code/wagtail_comses_net/settings/local.py"
if [ ! -f $LOCAL_PY ]; then
    echo "Copying $LOCAL_PY_TEMPLATE to $LOCAL_PY"
    cp -p $LOCAL_PY_TEMPLATE $LOCAL_PY
fi
chmod +x /code/deploy/app/*.sh
