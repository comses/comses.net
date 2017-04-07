#!/usr/bin/env python3

import sys
import shutil
import os
import binascii
import subprocess
import shlex
import argparse


def generate_key(size):
    return binascii.hexlify(os.urandom(size)).decode()


def generate_environment(build_type):
    db_name = 'comsesnet'
    db_password = generate_key(40)
    db_user = db_name
    django_secret_key = generate_key(40)
    discourse_sso_secret = generate_key(40)
    elasticsearch_path = '/etc/elasticsearch'

    mounts = dict(
        LIBRARY_ROOT='library',
        LOG_ROOT='logs',
        REPOSITORY_ROOT='repository',
        STATIC_ROOT='static',
        WEBPACK_ROOT='shared/webpack',
    )

    config = dict(
        DB_NAME=db_name,
        DB_HOST='db' if build_type == 'global' else 'localhost',
        DB_PASSWORD=db_password,
        DB_PORT='5432' if build_type == 'global' else '5434',
        DB_USER=db_user,
        DISCOURSE_SSO_SECRET=discourse_sso_secret,
        DJANGO_SECRET_KEY=django_secret_key,
        ELASTICSEARCH_PATH=elasticsearch_path,
        DOCKER_CODE_ROOT='/code'
    )

    docker_mounts = {"DOCKER_" + mount: os.path.join("/", mounts[mount]) for mount in mounts}
    host_mounts = {"HOST_" + mount: os.path.join("./deploy/local", mounts[mount]) for mount in mounts}
    config.update(docker_mounts)
    config.update(host_mounts)
    if build_type == 'local':
        config_mounts = {"CONFIG_" + mount: os.path.join("../deploy/local", mounts[mount]) for mount in mounts}
    elif build_type == 'global':
        config_mounts = {"CONFIG_" + mount: os.path.join("/", mounts[mount]) for mount in mounts}
    else:
        raise ValueError("build_type {} is invalid".format(build_type))

    config.update(config_mounts)
    return config


def substitute(in_file_name: str, out_file_name: str, environment):
    print("Templating {}".format(in_file_name))
    with open(in_file_name, 'r') as in_file:
        template = in_file.read()
        out_file_content = template.format(**environment)

    if os.path.exists(out_file_name):
        print("Backing up old '{}'".format(out_file_name))
        shutil.copy(out_file_name, out_file_name + '.backup')

    with open(out_file_name, 'w') as out_file:
        out_file.write(out_file_content)


def configure(build_type, compose_template, environment):
    compose = "generated-docker-compose-global.yml"
    config_ini_template = "deploy/conf/config.ini.debug.template"
    config_ini = config_ini_template.rsplit(".", 1)[0]

    if os.path.exists(config_ini):
        response = input(
            "Existing {} will be overwritten and you may lose access to existing containerized data. Continue?"
                .format(config_ini))
        if response.lower() not in ['y', 'yes']:
            return

    substitute(compose_template, compose, environment)
    substitute(config_ini_template, config_ini, environment)


parser = argparse.ArgumentParser(description='Build docker-compose and config.ini')
parser.add_argument('build_type', type=str, help='have django local (local) or in docker (global)')
parser.add_argument('compose_template', type=str, help='path to compose file template')

args = parser.parse_args()

environment = generate_environment(args.build_type)
configure(args.build_type, args.compose_template, environment)

command = 'docker-compose -f generated-docker-compose-global.yml build --pull --force-rm'.format(args.build_type)
print(command)
subprocess.run(shlex.split(command))
