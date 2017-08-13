FROM node:7

WORKDIR /code
COPY package.json /code
RUN npm install -g yarn && yarn install
COPY tsconfig.json /code/
CMD ["yarn", "run", "dev"]
