FROM node:lts-bookworm-slim

RUN apt-get update \
    && apt-get install -y libjpeg-turbo-progs \
    git \
    nasm \
    vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
COPY package.json yarn.lock /code/
RUN set -ex; yarn config set ignore-engines true; \
    if [ "$NODE_ENV" = "production" ]; then \
        yarn install --no-cache --frozen-lockfile --production; \
    elif [ "$NODE_ENV" = "test" ] || [ "$NODE_ENV" = "e2e" ]; then \
        yarn install --no-cache --frozen-lockfile; \
    else \
        yarn install; \
    fi
RUN yarn cache clean
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY vite.config.ts vitest.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json tsconfig.vitest.json .eslintrc.cjs .prettierrc /code/
# USER node
CMD ["yarn", "serve", "--port", "5000", "--host", "0.0.0.0"]
