FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
        curl \
        git \
        libffi-dev \
        libgit2-dev \
        libjpeg-turbo8-dev \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        postgresql-client \
        python3-dev \
        python3-pip \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && useradd -m comses -u 2718 \
# FIXME: scandir==1.4 dependency doesn't install cleanly in Docker for some reason
        && pip3 install hashfs --no-dependencies

ARG REQUIREMENTS_FILE=requirements-dev.txt
ENV PYTHONUNBUFFERED 1
COPY requirements.txt $REQUIREMENTS_FILE /tmp/
RUN pip3 install -r /tmp/$REQUIREMENTS_FILE

WORKDIR /code
CMD ["/code/deploy/app/dev.sh"]
