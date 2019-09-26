FROM node:12

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> etc/apt/sources.list.d/google.list'
RUN apt-get update && apt-get install -y google-chrome-stable realpath nasm libjpeg-turbo-progs vim

WORKDIR /code
COPY package.json /code
RUN yarn install
RUN yarn global add @vue/cli
# Separating to ensure that changes to the below files won't cause dependency reinstall
COPY babel.config.js cypress.json jest.config.js postcss.config.js tsconfig.json tslint.json vue.config.js /code/
CMD ["yarn", "serve", "--port", "3000", "--host", "0.0.0.0"]
