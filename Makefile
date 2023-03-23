DEPLOY_ENVIRONMENT := dev
DB_USER=comsesnet
DOCKER_SHARED_DIR=docker/shared
DOCKER_DB_DATA_DIR=docker/pgdata
BUILD_DIR=build
SECRETS_DIR=${BUILD_DIR}/secrets
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
SPARSE_REPO_URL=${SPARSE_REPO_URL}
SPARSE_REPO_PATH=${BUILD_DIR}/sparse-repo.tar.xz
REPO_BACKUPS_PATH=docker/shared/backups

include config.mk
include .env

.PHONY: build
build: docker-compose.yml secrets $(DOCKER_SHARED_DIR)
	docker compose build --pull

$(SPARSE_REPO_PATH):
	wget $(SPARSE_REPO_URL) -P ${BUILD_DIR}

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
	@echo "db password at $(DB_PASSWORD_PATH) was reset, may need to manually update existing db password"

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

$(SECRET_KEY_PATH): | ${SECRETS_DIR}
	SECRET_KEY=$$(openssl rand -base64 48); \
	echo "$${SECRET_KEY}" > $(SECRET_KEY_PATH)

docker-compose.yml: base.yml dev.yml staging.yml prod.yml config.mk $(PGPASS_PATH) .env
	case "$(DEPLOY_ENVIRONMENT)" in \
	  dev|staging) docker compose -f base.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
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
	docker compose pull db redis elasticsearch
ifneq ($(DEPLOY_ENVIRONMENT),dev)
	docker compose pull nginx
endif
	docker compose up -d 
	sleep 42
	docker compose exec server inv prepare

$(REPO_BACKUPS_PATH):
	@echo "$(REPO_BACKUPS_PATH) did not exist, creating now"
	mkdir -p $(REPO_BACKUPS_PATH)

.PHONY: restore
restore: build $(SPARSE_REPO_PATH) | $(REPO_BACKUPS_PATH)
	# take ownership of the repo path as it may have been created by root / docker
	# FIXME: this should get fixed if we do proper user management inside our server container
	sudo chown -R ${USER}: $(REPO_BACKUPS_PATH)
	# create repo directory if it doesn't exist
	mkdir -p $(REPO_BACKUPS_PATH)/repo
	# regardless of it existed, back it up to tmp dir
	@echo "Backing repo to /tmp directory"
	sudo mv $(REPO_BACKUPS_PATH)/repo $(shell mktemp -d)
	tar -Jxf $(SPARSE_REPO_PATH) -C $(REPO_BACKUPS_PATH)
	docker compose up -d
	docker compose exec server inv borg.restore

.PHONY: clean
clean:
	@echo "Backing up generated files to /tmp directory"
	mv .env config.mk docker-compose.yml $(CONFIG_INI_PATH) $(shell mktemp -d)

.PHONY: test
test: build
	docker compose run --rm server /code/deploy/test.sh
