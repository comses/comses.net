==========
Deployment
==========

This project is deployed and run using a multi-container Docker Compose workflow generated from repository config.

Source of truth
===============

- ``make deploy`` is the default deployment entrypoint.
- ``config.mk`` controls the active environment via ``DEPLOY_ENVIRONMENT``.
- ``docker-compose.yml`` is generated from ``base.yml`` plus environment overlays.

Environment selection
=====================

Set ``DEPLOY_ENVIRONMENT`` in ``config.mk``:

.. code-block:: make

	# dev|staging|test|prod
	DEPLOY_ENVIRONMENT=dev

Supported values:

- ``dev``
- ``staging``
- ``test``
- ``prod``

Configuration and state
=======================

- Runtime config: ``.env``
- Secrets: ``build/secrets/``
- Shared container data: ``docker/shared/`` (library files, media, backups, vite bundles, logs, and other shared assets)

Standard deployment workflow
============================

From repository root:

.. code-block:: bash

	make deploy

What ``make deploy`` does:

1. Builds and renders ``docker-compose.yml`` from selected environment files.
2. Builds images and ensures generated secrets/config files exist.
3. Pulls base services (and nginx for non-dev environments).
4. Starts services with Docker Compose.
5. Runs container preparation via ``docker compose exec server inv prepare``.

Common operational commands
===========================

.. code-block:: bash

	docker compose logs server
	docker compose exec server inv sh
	docker compose exec server ./manage.py <command>

Backup and restore
==================

Restore with ``make restore``
-----------------------------

Use ``make restore`` when you need to rebuild local state from a borg backup bundle.

.. code-block:: bash

	make restore

What it does:

1. Runs build prerequisites and ensures generated compose/config artifacts exist.
2. Uses ``build/repo.tar.xz`` if present, otherwise downloads from ``BORG_REPO_URL``.
3. Moves any existing ``docker/shared/backups/repo`` to a temporary directory for safety.
4. Extracts the selected backup archive into ``docker/shared/backups/``.
5. Starts services and runs ``docker compose exec server inv borg.restore``.

Set or update restore source in ``config.mk``:

.. code-block:: make

	BORG_REPO_URL=https://example.com/repo.tar.xz

General backup workflow
-----------------------

Before risky changes, create a fresh backup of DB + filesystem state from the running stack:

.. code-block:: bash

	docker compose exec server inv db.backup borg.init borg.backup

This creates/updates backup data under ``docker/shared/backups/repo``.

If you need to preserve that snapshot while testing another restore:

.. code-block:: bash

	mv docker/shared/backups/repo "$(mktemp -d /tmp/comses.XXXXXX)"

Later, move the saved repo back into ``docker/shared/backups/repo`` and run:

.. code-block:: bash

	docker compose exec server inv borg.restore

Safety notes
------------

- Restore operations replace active application state (DB + shared files).
- Treat restore as destructive to current local state unless you back up first.
- Keep backup/restore operations containerized and run from repository root.

Notes
=====

- Prefer ``docker compose`` (plugin) commands, not legacy ``docker-compose``.
- Regenerate deployment artifacts by updating ``config.mk`` and rerunning ``make deploy``.
- For a concise command index used by both humans and agents, see ``docs/agents/commands.md``.