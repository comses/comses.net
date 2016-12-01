FROM ubuntu:16.04

RUN apt-get update && apt-get install -y python3-dev libxml2-dev libgit2-dev postgresql-client \
        libpq-dev curl libxslt-dev python3-pip libffi-dev libjpeg-turbo8-dev \
        && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000

ENV PYTHONUNBUFFERED 1
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /code
CMD ["/code/deploy/app/dev.sh"]
