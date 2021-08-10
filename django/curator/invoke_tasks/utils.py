import logging
import os

logger = logging.getLogger(__name__)


env = {
    'python': 'python3',
    'project_name': 'cms',
    'project_conf': os.environ.get('DJANGO_SETTINGS_MODULE'),
    'coverage_omit_patterns': ('templates/*', 'settings/*', 'migrations/*', 'wsgi.py', 'management/*', 'tasks.py', 'apps.py'),
    'coverage_src_patterns': ('home', 'library', 'core',),
}


def dj(ctx, command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    ctx.run('{python} manage.py {dj_command} --settings {project_conf}'.format(dj_command=command, **env),
            **kwargs)
