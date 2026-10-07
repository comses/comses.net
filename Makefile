DOCKER_SHARED_DIR=$(COMSES_SHARED_ROOT)
# Writable shared paths. Deployed hosts provision these before Compose starts;
# this target retains the convenient repository-local behavior for development.
# `data` directory is used for direct postgres db server-side outputs, e.g., postgres COPY commands issued in
# ./manage.py export_raw_data
DOCKER_SHARED_SUBDIRS=.latest backups data extract incoming library media redis repository static statistics tests tls/well-known uploads vite
DOCKER_LOG_SUBDIRS=nginx

BUILD_DIR=build
SECRETS_DIR=${COMSES_SECRETS_ROOT}
DB_PASSWORD_PATH=${SECRETS_DIR}/db_password
PGPASS_PATH=${SECRETS_DIR}/.pgpass
SECRET_KEY_PATH=${SECRETS_DIR}/django_secret_key
DOWNLOAD_ANALYTICS_HMAC_KEY_PATH=${SECRETS_DIR}/download_analytics_hmac_key
EXT_SECRETS=borg_replication_ssh_key borg_replication_known_hosts hcaptcha_secret github_client_secret orcid_client_secret discourse_api_key discourse_sso_secret librarian_sso_secret mail_api_key datacite_api_password youtube_api_key github_integration_app_private_key github_integration_app_webhook_secret
GENERATED_SECRETS=$(DB_PASSWORD_PATH) $(PGPASS_PATH) $(SECRET_KEY_PATH) $(DOWNLOAD_ANALYTICS_HMAC_KEY_PATH)

ENVREPLACE := deploy/scripts/envreplace
DEPLOY_CONF_DIR=deploy/conf
ENV_TEMPLATE=${DEPLOY_CONF_DIR}/.env.template
DOCKER_BUILD_FLAGS ?=

# assumes a .tar.xz file
BORG_REPO_URL := https://example.com/repo.tar.xz
BORG_REPO_PATH=${BUILD_DIR}/repo.tar.xz
REPO_BACKUPS_PATH=${DOCKER_SHARED_DIR}/backups

# DEPLOY_ENVIRONMENT must be set in config.mk
include config.mk
include .env

# Resolve the physical checkout once for every Compose invocation, including
# rendering and recursive builds. Leave Compose project-name selection intact.
COMPOSE_ROOT := $(shell pwd -P)
COMPOSE := docker compose --project-directory "$(COMPOSE_ROOT)"
ifneq ($(filter staging prod,$(DEPLOY_ENVIRONMENT)),)
COMSES_APP_ROOT ?= /srv/apps/comses
COMSES_SHARED_ROOT ?= /srv/apps/comses/docker/shared
COMSES_POSTGRES_ROOT ?= /srv/apps/comses/docker/pgdata
COMSES_LOG_ROOT ?= /srv/logs/comses
COMSES_BACKUPS_ROOT ?= /srv/backups/comses
COMSES_SECRETS_ROOT ?= /srv/apps/comses/docker/secrets
else
COMSES_APP_ROOT ?= $(CURDIR)
COMSES_SHARED_ROOT ?= $(COMSES_APP_ROOT)/docker/shared
COMSES_POSTGRES_ROOT ?= $(COMSES_APP_ROOT)/docker/pgdata
COMSES_LOG_ROOT ?= $(COMSES_SHARED_ROOT)/logs
COMSES_SECRETS_ROOT ?= $(COMSES_APP_ROOT)/docker/secrets
endif

# Deployed hosts are provisioned explicitly; local and CI Compose bind mounts
# must exist because create_host_path is intentionally disabled.
COMPOSE_STORAGE_PREREQUISITES :=
ifeq ($(filter staging prod,$(DEPLOY_ENVIRONMENT)),)
COMPOSE_STORAGE_PREREQUISITES := $(DOCKER_SHARED_DIR) $(COMSES_POSTGRES_ROOT)
endif

PATH := $(HOME)/.local/bin:$(PATH)
# export all variables
# https://unix.stackexchange.com/questions/235223/makefile-include-env-file
# https://www.gnu.org/software/make/manual/html_node/Variables_002fRecursion.html
.EXPORT_ALL_VARIABLES:

.PHONY: build
build: docker-compose.yml secrets $(COMPOSE_STORAGE_PREREQUISITES)
	@$(COMPOSE) build --pull --parallel $(DOCKER_BUILD_FLAGS)

$(BORG_REPO_PATH):
	@mkdir -p $(@D)
	wget -c ${BORG_REPO_URL} -O $@

config.mk:
	@envsubst < ${DEPLOY_CONF_DIR}/config.mk.template > config.mk

.PHONY: $(DOCKER_SHARED_DIR)
$(DOCKER_SHARED_DIR):
	@for d in ${DOCKER_SHARED_SUBDIRS} ; do \
		mkdir -p ${DOCKER_SHARED_DIR}/$$d ; \
	done
	@# Elasticsearch writes as UID 1000. Once prepared, this subtree may not be traversable by the host user.
	@if [ ! -e ${DOCKER_SHARED_DIR}/elasticsearch ]; then \
		mkdir -p ${DOCKER_SHARED_DIR}/elasticsearch/primary ${DOCKER_SHARED_DIR}/elasticsearch/secondary ; \
		chmod 0777 ${DOCKER_SHARED_DIR}/elasticsearch ${DOCKER_SHARED_DIR}/elasticsearch/primary ${DOCKER_SHARED_DIR}/elasticsearch/secondary ; \
	elif [ -w ${DOCKER_SHARED_DIR}/elasticsearch ]; then \
		mkdir -p ${DOCKER_SHARED_DIR}/elasticsearch/primary ${DOCKER_SHARED_DIR}/elasticsearch/secondary ; \
		chmod 0777 ${DOCKER_SHARED_DIR}/elasticsearch ${DOCKER_SHARED_DIR}/elasticsearch/primary ${DOCKER_SHARED_DIR}/elasticsearch/secondary ; \
	fi
	@for d in ${DOCKER_LOG_SUBDIRS} ; do \
		mkdir -p ${COMSES_LOG_ROOT}/$$d ; \
	done

$(COMSES_POSTGRES_ROOT):
	@mkdir -p $@

${SECRETS_DIR}:
	@mkdir -p ${SECRETS_DIR}

$(SECRET_KEY_PATH): | ${SECRETS_DIR}
	@SECRET_KEY=$$(openssl rand -base64 48); \
	echo "$${SECRET_KEY}" > $(SECRET_KEY_PATH); \
	chmod 0600 $(SECRET_KEY_PATH)

$(DOWNLOAD_ANALYTICS_HMAC_KEY_PATH): | ${SECRETS_DIR}
	@umask 077; tmp=$$(mktemp "${SECRETS_DIR}/.download_analytics_hmac_key.XXXXXX"); \
	trap 'rm -f "$$tmp"' EXIT; \
	openssl rand -hex 32 > "$$tmp" && mv "$$tmp" "$@"

$(DB_PASSWORD_PATH): | ${SECRETS_DIR}
	@DB_PASSWORD=$$(openssl rand -base64 48); \
	TODAY=$$(date +%Y-%m-%d-%H:%M:%S); \
	if [ -f $(DB_PASSWORD_PATH) ]; \
	then \
	  cp "$(DB_PASSWORD_PATH)" "$(DB_PASSWORD_PATH)_$$TODAY"; \
	fi; \
	echo "$${DB_PASSWORD}" > $(DB_PASSWORD_PATH); \
	chmod 0600 $(DB_PASSWORD_PATH)
	@echo "db password at $(DB_PASSWORD_PATH) was reset, may need to manually update existing db password"

$(PGPASS_PATH): $(DB_PASSWORD_PATH) | ${SECRETS_DIR}
	@echo "${DB_HOST}:5432:*:${DB_USER}:$$(cat $(DB_PASSWORD_PATH))" > $(PGPASS_PATH)
	@chmod 0600 $(PGPASS_PATH)

.PHONY: release-version
release-version: .env
	@$(ENVREPLACE) RELEASE_VERSION $$(git describe --tags --abbrev=1 2>/dev/null || git rev-parse --short HEAD) .env
	@chmod 0600 .env

.env: $(DB_PASSWORD_PATH) $(SECRET_KEY_PATH)
	@if [ ! -f .env ]; then \
		cp $(ENV_TEMPLATE) .env; \
	fi; \
	# $(ENVREPLACE) DB_PASSWORD $$(cat $(DB_PASSWORD_PATH)) .env; \
	# $(ENVREPLACE) SECRET_KEY $$(cat $(SECRET_KEY_PATH)) .env; \
	$(ENVREPLACE) TEST_BASIC_AUTH_PASSWORD $$(openssl rand -base64 42) .env; \
	chmod 0600 .env

.PHONY: docker-compose.yml
docker-compose.yml: base.yml dev.yml staging.yml test.yml prod.yml config.mk \
	$(PGPASS_PATH) $(DOWNLOAD_ANALYTICS_HMAC_KEY_PATH) release-version .env $(COMPOSE_STORAGE_PREREQUISITES)
	@case "$(DEPLOY_ENVIRONMENT)" in \
	  dev|staging|test) $(COMPOSE) -f base.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  prod) $(COMPOSE) -f base.yml -f staging.yml -f $(DEPLOY_ENVIRONMENT).yml config > docker-compose.yml;; \
	  *) echo "invalid environment. must be either dev, staging or prod" 1>&2; exit 1;; \
	esac

.PHONY: set-db-password
set-db-password: $(DB_PASSWORD_PATH) .env
	$(COMPOSE) exec db psql comsesnet comsesnet -c "ALTER USER ${DB_USER} with password '$(shell cat ${DB_PASSWORD_PATH})';"

.PHONY: secrets
secrets: $(SECRETS_DIR) $(GENERATED_SECRETS)
	@for secret_path in $(EXT_SECRETS); do \
		touch ${SECRETS_DIR}/$$secret_path; \
		chmod 0600 ${SECRETS_DIR}/$$secret_path; \
	done

.PHONY: deploy
deploy:
	@deploy/scripts/storage-preflight
	+@$(MAKE) build
	$(COMPOSE) pull -q db redis elasticsearch
ifneq ($(DEPLOY_ENVIRONMENT),dev)
	$(COMPOSE) pull -q nginx
endif
	$(COMPOSE) up -d --quiet-pull
	sleep 42
	$(COMPOSE) exec server inv prepare

.PHONY: prepare-host-storage
prepare-host-storage:
	deploy/scripts/prepare-host-storage

.PHONY: storage-preflight
storage-preflight:
	@deploy/scripts/storage-preflight

.PHONY: test-storage-scripts
test-storage-scripts:
	deploy/scripts/tests/run-tests.sh

.PHONY: verify-compose-storage
verify-compose-storage: docker-compose.yml
	@deploy/scripts/verify-compose-storage

.PHONY: verify-container-storage
verify-container-storage: verify-compose-storage
	$(COMPOSE) run --rm --no-deps --entrypoint sh server -c 'grep -F " /shared " /proc/mounts && grep -F " /shared/logs " /proc/mounts && test -d /shared/backups && test ! -e /shared/postgres'
	$(COMPOSE) run --rm --no-deps --entrypoint sh db -c 'grep -F " /var/lib/postgresql/data " /proc/mounts'
ifneq ($(filter staging prod,$(DEPLOY_ENVIRONMENT)),)
	$(COMPOSE) run --rm --no-deps --entrypoint sh nginx -c 'grep -F " /var/log/nginx " /proc/mounts && grep -F " /srv/media " /proc/mounts'
endif

$(REPO_BACKUPS_PATH):
	@echo "$(REPO_BACKUPS_PATH) did not exist, creating now"
	mkdir -p $(REPO_BACKUPS_PATH)

.PHONY: restore
restore: build $(BORG_REPO_PATH) | $(REPO_BACKUPS_PATH)
	@stamp=$$(date -u +%Y%m%dT%H%M%SZ); \
	if [ -e $(REPO_BACKUPS_PATH)/repo ]; then \
		preserved=$(REPO_BACKUPS_PATH)/repo.pre-restore.$$stamp; \
		echo "Preserving existing Borg repository at $$preserved"; \
		sudo mv $(REPO_BACKUPS_PATH)/repo $$preserved; \
	fi
	sudo tar -Jxf $(BORG_REPO_PATH) -C $(REPO_BACKUPS_PATH)
	$(COMPOSE) up -d --quiet-pull
	$(COMPOSE) exec server inv borg.restore

.PHONY: clean
clean:
	@stamp=$$(date -u +%Y%m%dT%H%M%SZ); \
	destination=$(COMSES_SECRETS_ROOT)/generated-config-$$stamp; \
	install -d -m 0700 $$destination; \
	echo "Preserving generated configuration at $$destination"; \
	mv .env config.mk docker-compose.yml $$destination/

.PHONY: clean_deploy
clean_deploy: clean
	+@$(MAKE) deploy

.PHONY: test
test: build
	$(COMPOSE) run --quiet-pull --rm server /code/deploy/test.sh $(TEST_ARGS)

# e2e testing setup

E2E_SHARED_DIR=${DOCKER_SHARED_DIR}/e2e
E2E_BACKUPS_PATH=${E2E_SHARED_DIR}/backups
E2E_REPO_PATH=${E2E_BACKUPS_PATH}/repo

$(E2E_REPO_PATH):
	mkdir -p $(E2E_BACKUPS_PATH)
	wget -c --no-check-certificate ${BORG_REPO_URL} -P $(E2E_BACKUPS_PATH)
	tar -Jxf $(E2E_BACKUPS_PATH)/repo.tar.xz -C $(E2E_BACKUPS_PATH)

.PHONY: e2e
e2e: docker-compose.yml secrets $(DOCKER_SHARED_DIR) $(E2E_REPO_PATH)
	$(COMPOSE) -f docker-compose.yml -f e2e.yml build -q
	$(COMPOSE) -f docker-compose.yml -f e2e.yml up -d --quiet-pull
	sleep 42
	$(COMPOSE) -f docker-compose.yml -f e2e.yml exec server bash -c "\
		inv borg.restore --force && \
		inv prepare"

E2E_NPM_COMPOSE_RUN = $(COMPOSE) -f docker-compose.yml -f e2e.yml run --rm --no-deps -v "$(CURDIR)/e2e:/e2e" -w /e2e vite

.PHONY: e2e-deps-install-lock
e2e-deps-install-lock: docker-compose.yml
	$(E2E_NPM_COMPOSE_RUN) npm install --package-lock-only --no-audit --no-fund --cache /tmp/npm-global
	$(E2E_NPM_COMPOSE_RUN) npm ci --no-audit --no-fund --cache /tmp/npm-global

.PHONY: e2e-deps-update-lock
e2e-deps-update-lock: docker-compose.yml
	$(E2E_NPM_COMPOSE_RUN) npm update --package-lock-only --no-audit --no-fund --cache /tmp/npm-global
	$(E2E_NPM_COMPOSE_RUN) npm ci --no-audit --no-fund --cache /tmp/npm-global

.PHONY: e2e-deps
e2e-deps: e2e-deps-update-lock

.PHONY: gen-secret
gen-secret:
	@python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

.PHONY: check fix format
check:
	uv run ruff check .
	uv run ruff format . --check

fix:
	uv run ruff check . --fix
	uv run ruff format .

format:
	uv run ruff format .
