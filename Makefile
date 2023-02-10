include config.mk
include .env

DEPLOY_ENVIRONMENT = dev
DB_USER=comsesnet
DOCKER_SHARED_DIR=docker/shared
DOCKER_DB_DATA_DIR=docker/pgdata
SECRETS_DIR=build/secrets
DB_PASSWORD_PATH=${SECRETS_DIR}/db_password
PGPASS_PATH=${SECRETS_DIR}/.pgpass
SECRET_KEY_PATH=${SECRETS_DIR}/secret_key
SENTRY_DSN_PATH=${SECRETS_DIR}/sentry_dsn
DEPLOY_CONF_DIR=deploy/conf
PGPASS_TEMPLATE=${DEPLOY_CONF_DIR}/pgpass.template
CONFIG_INI_TEMPLATE=${DEPLOY_CONF_DIR}/config.ini.template
DOCKER_ENV_PATH=${DEPLOY_CONF_DIR}/docker.env
CONFIG_INI_PATH=${SECRETS_DIR}/config.ini
SENTRY_DSN=$(shell cat $(SENTRY_DSN_PATH))
MAIL_API_KEY_PATH=${SECRETS_DIR}/mail_api_key
SECRETS=$(MAIL_API_KEY_PATH) $(DB_PASSWORD_PATH) $(CONFIG_INI_PATH) $(PGPASS_PATH) $(SENTRY_DSN_PATH) $(SECRET_KEY_PATH) .env
SHARED_CONFIG_PATH=shared/src/assets/config.ts
BUILD_ID=$(shell git describe --tags --abbrev=1)

.PHONY: build
build: docker-compose.yml secrets $(DOCKER_SHARED_DIR)
	docker compose build --pull

config.mk:
	DEPLOY_ENVIRONMENT=${DEPLOY_ENVIRONMENT} envsubst < ${DEPLOY_CONF_DIR}/config.mk.template > config.mk


$(DOCKER_SHARED_DIR):
	for d in webpack logs library media static ; do \
		mkdir -p $(DOCKER_SHARED_DIR)/$$d ; \
	done
	mkdir -p $(DOCKER_DB_DATA_DIR)

${SECRETS_DIR}:
	mkdir -p ${SECRETS_DIR}

$(DB_PASSWORD_PATH): | ${SECRETS_DIR}
	DB_PASSWORD=$$(openssl rand -base64 48); \
	TODAY=$$(date +%Y-%m-%d-%H:%M:%S); \
	if [ -f $(DB_PASSWORD_PATH) ]; \
	then \
	  cp "$(DB_PASSWORD_PATH)" "$(DB_PASSWORD_PATH)_$$TODAY"; \
	fi; \
	echo "$${DB_PASSWORD}" > $(DB_PASSWORD_PATH)

$(SERVER_ENV): $(SERVER_ENV_TEMPLATE) $(SECRETS)
	POM_BASE_URL=${POM_BASE_URL} \
		envsubst < $(SERVER_ENV_TEMPLATE) > $(SERVER_ENV)
	
$(PGPASS_PATH): $(DB_PASSWORD_PATH) $(PGPASS_TEMPLATE) | ${SECRETS_DIR}
	DB_PASSWORD=$$(cat $(DB_PASSWORD_PATH)); \
	sed -e "s|DB_PASSWORD|$$DB_PASSWORD|" -e "s|DB_HOST|${DB_HOST}|" \
			-e "s|DB_USER|${DB_USER}|" $(PGPASS_TEMPLATE) > $(PGPASS_PATH)
	chmod 0600 $(PGPASS_PATH)

$(MAIL_API_KEY_PATH): | ${SECRETS_DIR}
	touch "$(MAIL_API_KEY_PATH)"

$(SENTRY_DSN_PATH): | ${SECRETS_DIR}
	touch "$(SENTRY_DSN_PATH)"

.env: $(DOCKER_ENV_PATH)
	cp ${DOCKER_ENV_PATH} .env

$(CONFIG_INI_PATH): .env $(DB_PASSWORD_PATH) $(CONFIG_INI_TEMPLATE) $(SECRET_KEY_PATH)
	DB_HOST=${DB_HOST} DB_NAME=${DB_NAME} DB_PASSWORD=$$(cat ${DB_PASSWORD_PATH}) \
	DB_USER=${DB_USER} DB_PORT=${DB_PORT} DJANGO_SECRET_KEY=$$(cat ${SECRET_KEY_PATH}) \
	TEST_USERNAME=___test_user___ TEST_BASIC_AUTH_PASSWORD=$$(openssl rand -base64 42) \
	TEST_USER_ID=1111111 BUILD_ID=${BUILD_ID} \
	envsubst < ${CONFIG_INI_TEMPLATE} > ${CONFIG_INI_PATH}
	# FIXME: should reset the db password too...

$(SECRET_KEY_PATH): | ${SECRETS_DIR}
	SECRET_KEY=$$(openssl rand -base64 48); \
	echo $${SECRET_KEY} > $(SECRET_KEY_PATH)

docker-compose.yml: base.yml staging.yml $(DEPLOY_ENVIRONMENT).yml config.mk $(PGPASS_PATH)
	case "$(DEPLOY_ENVIRONMENT)" in \
	  dev) docker compose -f base.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  staging) docker compose -f base.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  prod) docker compose -f base.yml -f staging.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  *) echo "invalid environment. must be either dev, staging or prod" 1>&2; exit 1;; \
	esac

.PHONY: set-db-password
set-db-password: $(DB_PASSWORD_PATH) $(CONFIG_INI_PATH)
	docker compose run --rm server psql -h db -U comsesnet comsesnet -c "ALTER USER ${DB_USER} with password '$(shell cat ${DB_PASSWORD_PATH})';"

.PHONY: secrets
secrets: $(SECRETS_DIR) $(SECRETS)

.PHONY: deploy
deploy: build
	docker compose up -d 

.PHONY: clean
clean:
# consider deleting build entirely but would lose generated secrets
	rm config.mk .env 

.PHONY: test
test: build
	docker compose run --rm server /code/deploy/test.sh
