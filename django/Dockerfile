FROM comses/base:0.9.22

ARG REQUIREMENTS_FILE=requirements-dev.txt
ARG RUN_SCRIPT=./deploy/dev.sh

RUN sed -i 's%archive.ubuntu.com%mirror.math.princeton.edu/pub%' /etc/apt/sources.list && \
        apt-get update && apt-get install -y \
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
        unzip && \
        update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 && \
        mkdir -p /etc/service/django && \
        touch /etc/service/django/run && \
        chmod a+x /etc/service/django/run

# install NLTK data into /usr/share/nltk_data
RUN pip3 install nltk && \
    curl -O https://dev.commons.asu.edu/nltk_data/data.zip && \
    unzip -q data.zip -d /tmp && \
    mkdir -p /usr/share/nltk_data && \
    mv /tmp/nltk_data-gh-pages/packages/* /usr/share/nltk_data/ && \
    find /usr/share/nltk_data -name '*.zip' -execdir unzip -q {} \;
#        python3 -m nltk.downloader -d /usr/share/nltk_data stopwords wordnet words verbnet maxent_ne_chunker names

COPY $REQUIREMENTS_FILE requirements.txt /tmp/
RUN pip3 install -r /tmp/$REQUIREMENTS_FILE && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY $RUN_SCRIPT /etc/service/django/run
WORKDIR /code
COPY . /code
CMD ["/sbin/my_init"]
