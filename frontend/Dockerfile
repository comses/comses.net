FROM node:8

WORKDIR /code
COPY package.json /code
RUN yarn install
COPY jest.json karma.conf.js tsconfig.json webpack.conf.js /code/
CMD ["yarn", "run", "dev"]
