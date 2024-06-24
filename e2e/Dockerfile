FROM cypress/base:18.14.1
WORKDIR /code

# only install dependencies if package.json or package-lock.json has changed
COPY package.json .
COPY package-lock.json .
COPY cypress.config.js .

# suppress most of the cypress messages
ENV CI=1

RUN npm install
