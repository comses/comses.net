#!/usr/bin/env bash

chmod a+x /code/deploy/*.sh;

/code/deploy/wait-for-it.sh cms:8000 -t 30 -- yarn run test-ci