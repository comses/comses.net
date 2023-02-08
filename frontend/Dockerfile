FROM node:lts-bullseye-slim

ENV NODE_OPTIONS=--openssl-legacy-provider

RUN apt-get update \
    && apt-get install -y nasm libjpeg-turbo-progs vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
COPY --chown=node:node package.json yarn.lock /code/
RUN set -ex; yarn config set ignore-engines true; \
    if [ "$NODE_ENV" = "production" ]; then \
        yarn install --no-cache --frozen-lockfile --production; \
    elif [ "$NODE_ENV" = "test" ]; then \
        yarn install --no-cache --frozen-lockfile; \
    else \
        yarn install; \
    fi
RUN yarn cache clean
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY --chown=node:node babel.config.js jest.config.js postcss.config.js tsconfig.json .eslintrc.js .prettierrc vue.config.js /code/
USER node
CMD ["yarn", "serve", "--port", "3000", "--host", "0.0.0.0"]
