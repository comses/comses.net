FROM node:8

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
RUN apt-get update && apt-get install -y google-chrome-stable

WORKDIR /code
COPY package.json /code
RUN yarn install
COPY karma.conf.js tsconfig.json webpack.conf.js .babelrc /code/
CMD ["yarn", "run", "dev"]
