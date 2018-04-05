FROM comses/base:1.1.0

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh
ARG UBUNTU_MIRROR=mirror.math.princeton.edu/pub

RUN sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
        && apt-get update \
        && apt-get install -y \
        autopostgresqlbackup \
        binutils \
        borgbackup \
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
        && touch /etc/service/django/run /etc/postgresql-backup-pre \
        && chmod a+x /etc/service/django/run /etc/postgresql-backup-pre \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ${REQUIREMENTS_FILE} requirements.txt /tmp/
RUN pip3 install -r /tmp/${REQUIREMENTS_FILE} --no-cache-dir \
        && python -m nltk.downloader stopwords \
        && python -m nltk.downloader punkt
COPY ./deploy/db/autopostgresqlbackup /etc/cron.daily/autopostgresqlbackup
COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ./deploy/db/postgresql-backup-pre /etc/
COPY ./deploy/logrotate.d/* /etc/logrotate.d/
COPY ${RUN_SCRIPT} /etc/service/django/run
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
