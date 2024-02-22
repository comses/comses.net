DEPLOY_ENVIRONMENT := dev

DOCKER_SHARED_DIR=docker/shared
DOCKER_DB_DATA_DIR=docker/pgdata

BUILD_DIR=build
SECRETS_DIR=${BUILD_DIR}/secrets
DB_PASSWORD_PATH=${SECRETS_DIR}/db_password
PGPASS_PATH=${SECRETS_DIR}/.pgpass
SECRET_KEY_PATH=${SECRETS_DIR}/django_secret_key
EXT_SECRETS=mailgun_api_key hcaptcha_secret github_client_secret orcid_client_secret discourse_api_key discourse_sso_secret mail_api_key
GENERATED_SECRETS=$(DB_PASSWORD_PATH) $(PGPASS_PATH) $(SECRET_KEY_PATH)

ENVREPLACE := deploy/scripts/envreplace
DEPLOY_CONF_DIR=deploy/conf
ENV_TEMPLATE=${DEPLOY_CONF_DIR}/.env.template

# assumes a .tar.xz file
BORG_REPO_URL := https://example.com/repo.tar.xz
BORG_REPO_PATH=${BUILD_DIR}/sparse-repo.tar.xz
REPO_BACKUPS_PATH=docker/shared/backups

include config.mk
include .env

# export all variables
# https://unix.stackexchange.com/questions/235223/makefile-include-env-file
# https://www.gnu.org/software/make/manual/html_node/Variables_002fRecursion.html
.EXPORT_ALL_VARIABLES:

.PHONY: build
build: docker-compose.yml secrets $(DOCKER_SHARED_DIR)
	docker compose build --pull

$(BORG_REPO_PATH):
	wget ${BORG_REPO_URL} -P ${BUILD_DIR}

config.mk:
	DEPLOY_ENVIRONMENT=${DEPLOY_ENVIRONMENT} envsubst < ${DEPLOY_CONF_DIR}/config.mk.template > config.mk

.PHONY: $(DOCKER_SHARED_DIR)
$(DOCKER_SHARED_DIR):
	for d in vite logs library media static ; do \
		mkdir -p ${DOCKER_SHARED_DIR}/$$d ; \
	done
	mkdir -p ${DOCKER_DB_DATA_DIR}

${SECRETS_DIR}:
	mkdir -p ${SECRETS_DIR}

$(SECRET_KEY_PATH): | ${SECRETS_DIR}
	SECRET_KEY=$$(openssl rand -base64 48); \
	echo "$${SECRET_KEY}" > $(SECRET_KEY_PATH)

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
	echo "${DB_HOST}:5432:*:${DB_USER}:$$(cat $(DB_PASSWORD_PATH))" > $(PGPASS_PATH)
	chmod 0600 $(PGPASS_PATH)

.PHONY: release-version
release-version: .env
	$(ENVREPLACE) RELEASE_VERSION $$(git describe --tags --abbrev=1) .env

.env: $(DB_PASSWORD_PATH) $(SECRET_KEY_PATH)
	if [ ! -f .env ]; then \
		cp $(ENV_TEMPLATE) .env; \
	fi; \
	# $(ENVREPLACE) DB_PASSWORD $$(cat $(DB_PASSWORD_PATH)) .env; \
	# $(ENVREPLACE) SECRET_KEY $$(cat $(SECRET_KEY_PATH)) .env; \
	$(ENVREPLACE) TEST_BASIC_AUTH_PASSWORD $$(openssl rand -base64 42) .env

.PHONY: docker-compose.yml
docker-compose.yml: base.yml dev.yml staging.yml prod.yml config.mk $(PGPASS_PATH) release-version
	case "$(DEPLOY_ENVIRONMENT)" in \
	  dev|staging|e2e) docker compose -f base.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  prod) docker compose -f base.yml -f staging.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  *) echo "invalid environment. must be either dev, staging or prod" 1>&2; exit 1;; \
	esac

.PHONY: set-db-password
set-db-password: $(DB_PASSWORD_PATH) .env
	docker compose run --rm server psql -h db -U comsesnet comsesnet -c "ALTER USER ${DB_USER} with password '$(shell cat ${DB_PASSWORD_PATH})';"

.PHONY: secrets
secrets: $(SECRETS_DIR) $(GENERATED_SECRETS)
	for secret_path in $(EXT_SECRETS); do \
		touch ${SECRETS_DIR}/$$secret_path; \
	done

.PHONY: deploy
deploy: build .env
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
restore: build $(BORG_REPO_PATH) | $(REPO_BACKUPS_PATH)
	# take ownership of the repo path as it may have been created by root / docker
	# FIXME: this should be fixed if we have proper user management inside our server container
	sudo chown -R ${USER}: $(REPO_BACKUPS_PATH)
	# create repo directory if it doesn't exist
	mkdir -p $(REPO_BACKUPS_PATH)/repo
	# regardless of it existed, back it up to tmp dir
	@echo "Backing existing ${REPO_BACKUPS_PATH}/repo to fresh mktemp directory in /tmp"
	sudo mv $(REPO_BACKUPS_PATH)/repo $(shell mktemp -d)
	tar -Jxf $(BORG_REPO_PATH) -C $(REPO_BACKUPS_PATH)
	docker compose up -d
	docker compose exec server inv borg.restore

.PHONY: clean
clean:
	@echo "Backing up generated files to /tmp directory"
	mv .env config.mk docker-compose.yml $(shell mktemp -d)

.PHONY: clean_deploy
clean_deploy: clean
	+@$(MAKE) deploy

.PHONY: test
test: build
	docker compose run --rm server /code/deploy/test.sh

.PHONY: e2e
e2e: DEPLOY_ENVIRONMENT=e2e
e2e: build
	docker compose run server inv collectstatic
	docker compose run --rm e2e npm run test
	docker compose down
