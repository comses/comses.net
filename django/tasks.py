from distutils.util import strtobool

from invoke import task
from invoke.tasks import call

import logging
import os
import pathlib
import sys

# push current directory onto the path to access core.settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

from django.conf import settings

env = {
    'python': 'python3',
    'project_name': 'cms',
    'db_name': settings.DATABASES['default']['NAME'],
    'db_host': settings.DATABASES['default']['HOST'],
    'db_user': settings.DATABASES['default']['USER'],
    'project_conf': os.environ.get('DJANGO_SETTINGS_MODULE'),
    'coverage_omit_patterns': ('test', 'settings', 'migrations', 'wsgi', 'management', 'tasks', 'apps.py'),
    'coverage_src_patterns': ('home', 'library', 'core',),
}

logger = logging.getLogger(__name__)


def dj(ctx, command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    ctx.run('{python} manage.py {dj_command} --settings {project_conf}'.format(dj_command=command, **env),
            **kwargs)


@task
def clean_update(ctx):
    ctx.run("git fetch --all && git reset --hard origin/master")


@task
def clean(ctx, revert=False):
    ctx.run("find . -name '*.pyc' -o -name 'generated-*' -delete -print")
    if revert:
        clean_update(ctx)


@task(aliases=['cs'])
def collect_static(ctx):
    dj(ctx, 'collectstatic -c --noinput', pty=True)


@task(aliases=['qc'])
def quality_check_openabm_files_with_db(ctx):
    dj(ctx, 'quality_check_files_with_db', pty=True)


@task
def sh(ctx, print_sql=False):
    dj(ctx, 'shell_plus --ipython{}'.format(' --print-sql' if print_sql else ''), pty=True)


@task
def test(ctx, tests=None, coverage=False):
    if tests is not None:
        apps = tests
    else:
        apps = ''
    if coverage:
        ignored = ['*{0}*'.format(ignored_pkg) for ignored_pkg in env['coverage_omit_patterns']]
        coverage_cmd = "coverage run --source={0} --omit={1}".format(','.join(env['coverage_src_patterns']),
                                                                     ','.join(ignored))
    else:
        coverage_cmd = env['python']
    ctx.run("{coverage_cmd} manage.py test {apps}".format(apps=apps, coverage_cmd=coverage_cmd),
            env={'DJANGO_SETTINGS_MODULE': 'core.settings.test', 'HYPOTHESIS_VERBOSITY_LEVEL': 'verbose'})


@task(pre=[call(test, coverage=True)])
def coverage(ctx):
    ctx.run('coverage html')


@task
def server(ctx, ip="0.0.0.0", port=8000):
    dj(ctx, 'runserver {ip}:{port}'.format(ip=ip, port=port), capture=False)


@task(aliases=['ss'])
def setup_site(ctx, site_name='CoRe @ CoMSES Net', site_domain='www.comses.net'):
    dj(ctx, 'setup_site --site-name="{0}" --site-domain="{1}"'.format(site_name, site_domain))
    if not settings.DEPLOY_ENVIRONMENT.is_production():
        deny_robots(ctx)


@task(aliases=['idd'])
def import_drupal_data(ctx, directory='/shared/incoming'):
    dj(ctx, 'import_drupal_data -d {0}'.format(directory))


@task(aliases=['icf'])
def import_codebase_files(ctx, directory='/shared/incoming/models'):
    dj(ctx, 'import_codebase_files -d {0}'.format(directory))


@task(import_drupal_data, import_codebase_files, setup_site, aliases=['ima'])
def import_all(ctx):
    pass


@task(aliases=['esli'])
def update_elasticsearch_license(ctx, license='/secrets/es5-license.json'):
    for elasticsearch_host in ('elasticsearch', 'elasticsearch2'):
        ctx.run(
            "curl -XPUT 'http://{0}:9200/_xpack/license?acknowledge=true' -H 'Content-Type: application/json' -d @{1}".format(
                elasticsearch_host, license))


@task(aliases=['pgpass'])
def create_pgpass_file(ctx, force=False):
    pgpass_path = os.path.join(os.path.expanduser('~'), '.pgpass')
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, 'w+') as pgpass:
        db_password = settings.DATABASES['default']['PASSWORD']
        pgpass.write('db:*:*:{db_user}:{db_password}\n'.format(db_password=db_password, **env))
        ctx.run('chmod 0600 ~/.pgpass')


@task(aliases=['dr'])
def deny_robots(ctx):
    dj(ctx, 'setup_robots_txt --no-allow')


@task
def backup(ctx):
    create_pgpass_file(ctx)
    ctx.run('/usr/sbin/autopostgresqlbackup')


@task(aliases=['idb', 'initdb'])
def run_migrations(ctx, clean=False, initial=False):
    apps = ('core', 'home', 'library')
    if clean:
        for app in apps:
            migration_dir = os.path.join(app, 'migrations')
            ctx.run('find {0} -name 00*.py -delete -print'.format(migration_dir))
    dj(ctx, 'makemigrations citation --noinput')
    dj(ctx, 'makemigrations {0} --noinput'.format(' '.join(apps)))
    migrate_command = 'migrate --noinput'
    if initial:
        migrate_command += ' --fake-initial'
    dj(ctx, migrate_command)


@task(aliases=['ddb', 'dropdb'])
def drop_database(ctx, create=False):
    create_pgpass_file(ctx)
    ctx.run('psql -h {db_host} -c "alter database {db_name} connection limit 1;" -w {db_name} {db_user}'.format(**env),
            echo=True, warn=True)
    ctx.run(
        'psql -h {db_host} -c "select pg_terminate_backend(pid) from pg_stat_activity where datname=\'{db_name}\'" -w {db_name} {db_user}'.format(
            **env),
        echo=True, warn=True)
    ctx.run('dropdb -w --if-exists -e {db_name} -U {db_user} -h {db_host}'.format(**env), echo=True, warn=True)
    if create:
        ctx.run('createdb -w {db_name} -U {db_user} -h {db_host}'.format(**env), echo=True, warn=True)


@task(aliases=['rfd', 'restore'])
def restore_from_dump(ctx, dumpfile='comsesnet.sql', migrate=True):
    confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
        dumpfile))
    dumpfile_path = pathlib.Path(dumpfile)
    if dumpfile.endswith('.sql') and dumpfile_path.is_file():
        drop_database(ctx, create=True)
        ctx.run('psql -w -q -h db {db_name} {db_user} < {dumpfile}'.format(dumpfile=dumpfile, **env),
                warn=True)
    if migrate:
        run_migrations(ctx, clean=True, initial=True)


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        logger.info("Invalid response %s. Please confirm with yes (y) or no (n).", response_as_bool)
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)


@task(aliases=['rdb', 'resetdb'])
def reset_database(ctx):
    drop_database(ctx, create=True)
    run_migrations(ctx, False)
