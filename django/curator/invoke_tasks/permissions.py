from invoke import task
from .utils import dj

@task(aliases=['edperm'])
def setup_editor_permissions(ctx):
    dj(ctx, 'setup_editor_permissions')
