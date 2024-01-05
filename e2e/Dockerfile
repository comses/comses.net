FROM cypress/base:18.14.1
WORKDIR /code

# only install dependencies if package.json or package-lock.json has changed
COPY package.json .
COPY package-lock.json .

# suppress most of the cypress messages
ENV CI=1

RUN npm install

# verify that cypress is installed correctly
RUN npm run cy:run -- verify
