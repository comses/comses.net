FROM node:8

WORKDIR /code
COPY package.json /code
RUN yarn install
COPY jest.json tsconfig.json webpack.conf.js /code/
CMD ["yarn", "run", "dev"]
