FROM comses/base:jammy

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh
ARG UBUNTU_MIRROR=mirror.arizona.edu/ubuntu

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
        && apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
        && install -d /usr/share/postgresql-common/pgdg && curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
        autopostgresqlbackup \
        binutils \
        borgbackup \
        clamav \
        clamav-daemon \
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
        python3-venv \
        unrar-free \
        unzip \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && apt-get upgrade -y -o Dpkg::Options::="--force-confold" \
        && mkdir -p /etc/service/django \
        && touch /etc/service/django/run /etc/postgresql-backup-pre \
        && chmod a+x /etc/service/django/run /etc/postgresql-backup-pre \
        && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
COPY ${REQUIREMENTS_FILE} requirements.txt /tmp/

# FIXME: change to container user
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip3 install -r /tmp/${REQUIREMENTS_FILE} \ 
    && touch /code/override.env

COPY ./deploy/cron.daily/* /etc/cron.daily/
COPY ./deploy/cron.hourly/* /etc/cron.hourly/
COPY ./deploy/cron.weekly/* /etc/cron.weekly/
COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ./deploy/db/postgresql-backup-pre /etc/
COPY ${RUN_SCRIPT} /etc/service/django/run
COPY . /code
CMD ["/sbin/my_init"]
