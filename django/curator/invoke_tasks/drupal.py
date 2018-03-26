from invoke import task
from .base import setup_site
from .util import dj

@task(aliases=['idd'])
def import_drupal_data(ctx, directory='/shared/incoming'):
    dj(ctx, 'import_drupal_data -d {0}'.format(directory))


@task(aliases=['icf'])
def import_codebase_files(ctx, directory='/shared/incoming/models'):
    dj(ctx, 'import_codebase_files -d {0}'.format(directory))


@task(import_drupal_data, import_codebase_files, setup_site, aliases=['ima'])
def import_all(ctx):
    pass
