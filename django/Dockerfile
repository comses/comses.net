FROM comses/base:1.3.0

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh
ARG UBUNTU_MIRROR=mirror.arizona.edu/ubuntu

RUN sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
        && apt-get update \
        && apt-get install -y \
        autopostgresqlbackup \
        binutils \
        borgbackup \
        clamav \
        clamav-daemon \
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
        && apt-get upgrade -y -o Dpkg::Options::="--force-confold" \
        && mkdir -p /etc/service/django \
        && pip3 install -U pip \
        && touch /etc/service/django/run /etc/postgresql-backup-pre \
        && chmod a+x /etc/service/django/run /etc/postgresql-backup-pre \
        && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ${REQUIREMENTS_FILE} requirements.txt /tmp/
RUN pip3 install -r /tmp/${REQUIREMENTS_FILE} --no-cache-dir
COPY ./deploy/cron.daily/* /etc/cron.daily/
COPY ./deploy/cron.hourly/* /etc/cron.hourly/
COPY ./deploy/cron.weekly/* /etc/cron.weekly/
COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ./deploy/db/postgresql-backup-pre /etc/
COPY ${RUN_SCRIPT} /etc/service/django/run
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
