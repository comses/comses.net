FROM node:lts-bookworm-slim

WORKDIR /code
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends -o=Dpkg::Use-Pty=0 libjpeg-turbo-progs \
    git \
    nasm \
    vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY package.json package-lock.json /code/
RUN set -ex;  \
    if [ "$NODE_ENV" = "production" ]; then \
        npm install --production --no-progress --loglevel=warn; \
    elif [ "$NODE_ENV" = "test" ] || [ "$NODE_ENV" = "e2e" ]; then \
        npm ci --no-progress --loglevel=warn; \
    else \
        npm install --no-progress --loglevel=warn; \
    fi
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY vite.config.ts vitest.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json tsconfig.vitest.json .eslintrc.cjs .prettierrc /code/
# USER node
CMD ["npm", "start"]
