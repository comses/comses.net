FROM comses/base:phusion

RUN apt-get update && apt-get install -y \
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
        unrar-free && \
        update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 && \
        mkdir -p /etc/service/django 

ARG REQUIREMENTS_FILE=requirements-dev.txt

COPY $REQUIREMENTS_FILE requirements.txt /tmp/
COPY ./deploy/dev.sh /etc/service/django/run
RUN pip3 install -r /tmp/$REQUIREMENTS_FILE && \
    chmod a+x /etc/service/django/run && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# FIXME: run as restricted user, remove unnecessary packages
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
