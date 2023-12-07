FROM node:lts-bookworm-slim

ENV YARN_VERSION stable

WORKDIR /code
RUN apt-get update \
    && apt-get install -y libjpeg-turbo-progs \
    git \
    nasm \
    vim \
    && corepack enable && yarn set version $YARN_VERSION \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY package.json yarn.lock .yarnrc.yml /code/
RUN set -ex;  \
    if [ "$NODE_ENV" = "production" ]; then \
        yarn workspaces focus --production; \
    elif [ "$NODE_ENV" = "test" ] || [ "$NODE_ENV" = "e2e" ]; then \
        yarn install --immutable; \
    else \
        yarn install; \
    fi
RUN yarn cache clean
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY vite.config.ts vitest.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json tsconfig.vitest.json .eslintrc.cjs .prettierrc /code/
# USER node
CMD ["yarn", "serve", "--port", "5000", "--host", "0.0.0.0"]
