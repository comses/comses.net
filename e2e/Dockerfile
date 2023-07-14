FROM cypress/base:18.14.1
WORKDIR /code

# only install dependencies if package.json or yarn.lock has changed
COPY package.json .
COPY yarn.lock .

# suppress most of the cypress messages
ENV CI=1

RUN yarn install --frozen-lockfile

# verify that cypress is installed correctly
RUN yarn cypress verify
