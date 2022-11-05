FROM node:lts-bullseye

RUN apt-get update \
    && apt-get install -y nasm libjpeg-turbo-progs vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
ENV NODE_OPTIONS=--openssl-legacy-provider
COPY package.json yarn.lock /code/
RUN set -ex; \
    if [ "$NODE_ENV" = "production" ]; then \
        yarn install --no-cache --frozen-lockfile --production; \
    elif [ "$NODE_ENV" = "test" ]; then \
        yarn install --no-cache --frozen-lockfile; \
    else \
        yarn install; \
    fi
RUN yarn global add @vue/cli && yarn cache clean
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY babel.config.js jest.config.js postcss.config.js tsconfig.json tslint.json vue.config.js /code/
CMD ["yarn", "serve", "--port", "3000", "--host", "0.0.0.0"]
