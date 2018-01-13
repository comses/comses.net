FROM comses/base:1.0.1

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh
ENV UBUNTU_MIRROR=mirror.math.princeton.edu/pub

RUN sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list && \
        apt-get update && apt-get install -y \
        autopostgresqlbackup \
        binutils \
        curl \
        gdal-bin \
        git \
        libffi-dev \
        libgeoip1 \
        libgit2-dev \
        libjpeg-turbo8-dev \
        libproj-dev \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        postgresql-client \
        python3-dev \
        python3-gdal \
        python3-pip \
        python3-setuptools \
        unrar-free \
        unzip \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && mkdir -p /etc/service/django \
        && touch /etc/service/django/run \
        && chmod a+x /etc/service/django/run \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ${REQUIREMENTS_FILE} requirements.txt /tmp/
COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ${RUN_SCRIPT} /etc/service/django/run
RUN pip3 install -r /tmp/${REQUIREMENTS_FILE} --no-cache-dir
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
