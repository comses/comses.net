FROM node:8-wheezy

RUN apt-get update && apt-get install -y chromium

WORKDIR /code
COPY package.json /code
RUN yarn install
COPY karma.conf.js tsconfig.json tsconfig_test.json webpack.conf.js .babelrc /code/
CMD ["yarn", "run", "dev"]
