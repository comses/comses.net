ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh
ARG UBUNTU_MIRROR=archive.ubuntu.com
ARG BASE_IMAGE=phusion/baseimage:noble-1.0.2

FROM ${BASE_IMAGE} AS base

ARG UBUNTU_MIRROR
ENV VIRTUAL_ENV=/home/comses/virtualenvs/comses.venv
# FIXME: this gets overridden by values in .env
ENV PATH=/usr/lib/postgresql/16/bin:${VIRTUAL_ENV}/bin:$PATH

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

FROM base AS builder

RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    DEBIAN_FRONTEND=noninteractive \
    sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
        && apt-get -qq update \
        && apt-get -qq install -y --no-install-recommends -o=Dpkg::Use-Pty=0 \
        build-essential \
        ca-certificates \
        git \
        libacl1-dev \
        libffi-dev \
        libjpeg-turbo8-dev \
        liblz4-dev \
        libpq-dev \
        libssl-dev \
        libxml2-dev \
        libxslt-dev \
        libxxhash-dev \
        libzstd-dev \
        pkg-config \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-venv \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && python -m venv ${VIRTUAL_ENV} \
        && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ARG REQUIREMENTS_FILE
COPY ${REQUIREMENTS_FILE} requirements.txt /tmp/

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --progress-bar off -r /tmp/${REQUIREMENTS_FILE}

FROM base AS runtime

RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    DEBIAN_FRONTEND=noninteractive \
    sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
        && apt-get -qq update \
        && apt-get -qq install -y --no-install-recommends -o=Dpkg::Use-Pty=0 postgresql-common \
        && yes | /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh \
        && apt-get -qq update \
        && apt-get -qq install -y --no-install-recommends -o=Dpkg::Use-Pty=0 \
        ca-certificates \
        clamav \
        clamav-daemon \
        curl \
        git \
        libacl1 \
        libgeoip1 \
        liblz4-1 \
        libpython3.12t64 \
        libssl3t64 \
        libxxhash0 \
        libzstd1 \
        openssh-client \
        postgresql-client-16 \
        python3 \
        rsync \
        unrar-free \
        unzip \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && useradd -m --uid 2718 comses \
        && mkdir -p /etc/service/django /etc/service/huey \
        && touch /etc/service/django/run /etc/service/huey/run \
        && chmod a+x /etc/service/django/run /etc/service/huey/run \
        && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
# A stable path also works for cron and commands outside the application venv.
RUN ln -s ${VIRTUAL_ENV}/bin/borg /usr/local/bin/borg && borg --version

WORKDIR /code

COPY ./deploy/cron.daily/* /etc/cron.daily/
COPY ./deploy/cron.hourly/* /etc/cron.hourly/
COPY ./deploy/cron.weekly/* /etc/cron.weekly/
ARG RUN_SCRIPT
COPY ${RUN_SCRIPT} /etc/service/django/run
COPY ./deploy/huey.sh /etc/service/huey/run
COPY . /code

CMD ["/sbin/my_init"]
