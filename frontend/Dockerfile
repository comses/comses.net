FROM node:lts-bookworm-slim AS deps

WORKDIR /code
COPY package.json package-lock.json /code/
RUN npm ci --no-progress --loglevel=warn

FROM deps AS dev
COPY . /code/
CMD ["npm", "start"]

FROM deps AS build
COPY . /code/
