FROM comses/base

RUN apt-get update && apt-get install -q -y \
        curl \
        git \
        npm \
        libffi-dev \
        libgit2-dev \
        libjpeg-turbo8-dev \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        postgresql-client \
        python3-dev \
        python3-pip \
        unrar-free \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
        && locale-gen en_US.UTF-8

ARG REQUIREMENTS_FILE=requirements-dev.txt
ENV PYTHONUNBUFFERED=1 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8
WORKDIR /code
COPY requirements.txt $REQUIREMENTS_FILE /tmp/
RUN pip3 install -r /tmp/$REQUIREMENTS_FILE
RUN apt-get install -y nodejs && cd /usr/bin && ln -s nodejs node && cd /code
COPY frontend/package.json frontend/package.json
RUN cd frontend && npm install && cd ..
# FIXME: run as restricted user, remove unnecessary packages
CMD ["/code/deploy/app/dev.sh"]
