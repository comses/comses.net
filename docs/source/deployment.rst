==========
Deployment
==========

---------------------------
Compute Canada provisioning
---------------------------

Our infrastructure is currently hosted on Compute Canada's east cloud (catalog app, staging) & west cloud (arbutus, result from Resource Allocation Grant with Dawn)

- production deployed on West Cloud allocation (arbutus)
- create or import keypairs if necessary
- launch desired instance (e.g., ubuntu 16.04 amd image) and make sure to associate the keypair with the image in the tab
- create volume & attach to instance
- associate floating IP to instance

Notes
=====

- Set docker location in ``/etc/docker/daemon.json`` to large volume mountpoint, e.g., `/mnt/docker` see https://github.com/moby/moby/issues/3127 for more details.

Steps
=====

- checkout latest stable release from git
- double check .env and appropriately symlinked docker-compose.yml file or run ``./build.sh`` first.
- ``docker-compose pull --ignore-pull-failure``
- ``docker-compose build --pull``
- ``docker-compose up -d``
- Upgrade DB if necessary: ``./manage.py makemigrations && ./manage.py migrate``
- Rebuild elasticsearch index: ``./manage.py update_index``
- Move generated javascript and static assets: ``./manage.py collectstatic -c --noinput``