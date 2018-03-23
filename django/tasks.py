from invoke import task
from invoke.tasks import call

import logging
import os
import sys

# push current directory onto the path to access core.settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

from django.conf import settings
from curator.invoke_tasks import dj, create_pgpass_file, run_migrations, drop_database, restore_from_dump, restore, create_archive, env

logger = logging.getLogger(__name__)


@task
def clean(ctx, revert=False):
    ctx.run("find . -name '*.pyc' -o -name 'generated-*' -delete -print")


@task(aliases=['cs'])
def collect_static(ctx):
    dj(ctx, 'collectstatic -c --noinput', pty=True)
    ctx.run('touch ./core/wsgi.py')


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


@task(aliases=['dr'])
def deny_robots(ctx):
    dj(ctx, 'setup_robots_txt --no-allow')


@task(aliases=['rdb', 'resetdb'])
def reset_database(ctx):
    drop_database(ctx, create=True)
    run_migrations(ctx, False)


@task(iterable=['my_list'])
def mytask(ctx, my_list):
    print(my_list)