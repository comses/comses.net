FROM node:lts-bookworm-slim

WORKDIR /code
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends -o=Dpkg::Use-Pty=0 libjpeg-turbo-progs \
    git \
    nasm \
    vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY package.json package-lock.json /code/
RUN npm ci --no-progress --loglevel=warn
COPY . /code/
# USER node
CMD ["npm", "start"]
