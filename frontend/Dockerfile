FROM node:7

WORKDIR /code
COPY package.json /code
RUN npm install -g yarn && yarn install
COPY tsconfig.json typings.json /code/
COPY build /code/build
COPY config /code/config
CMD ["yarn", "run", "dev"]
