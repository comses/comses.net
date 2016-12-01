FROM comses/base

RUN apk add --no-cache musl-dev gcc python3-dev libxml2-dev libxslt-dev build-base pcre-dev linux-headers \
# utility dependencies
        curl git bash ssmtp mailx libgit2-dev libffi-dev libjpeg-turbo-dev postgresql-client postgresql-dev

ENV PYTHONUNBUFFERED 1
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /code
CMD ["/code/deploy/app/dev.sh"]
