FROM comses/base

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh

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
        mkdir -p /etc/service/django && \
        touch /etc/service/django/run && \
        chmod a+rx /etc/service/django/run

COPY $REQUIREMENTS_FILE requirements.txt /tmp/
RUN pip3 install -r /tmp/$REQUIREMENTS_FILE && \
# install NLTK data into /usr/share/nltk_data
    python3 -m nltk.downloader -d /usr/share/nltk_data \
        punkt stopwords wordnet words verbnet averaged_perceptron_tagger maxent_ne_chunker names && \
    chmod a+x /etc/service/django/run && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY $RUN_SCRIPT /etc/service/django/run
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
