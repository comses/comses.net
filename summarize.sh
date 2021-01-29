#!/usr/bin/env bash

docker run -it --rm -v $PWD/reports:/home/analytics -v $PWD/docker/shared/statistics:/shared/statistics -w /home/analytics rocker/tidyverse Rscript members.R
