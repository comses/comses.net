import logging
import os

from distutils.util import strtobool

logger = logging.getLogger(__name__)


class ChDir:
    def __init__(self, path):
        self.new_path = path
        self.old_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.old_path)


env = {
    'python': 'python3',
    'project_name': 'cms',
    'project_conf': os.environ.get('DJANGO_SETTINGS_MODULE'),
    'coverage_omit_patterns': ('test', 'settings', 'migrations', 'wsgi', 'management', 'tasks', 'apps.py'),
    'coverage_src_patterns': ('home', 'library', 'core',),
}


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        logger.info("Invalid response %s. Please confirm with yes (y) or no (n).", response_as_bool)
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)


def dj(ctx, command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    ctx.run('{python} manage.py {dj_command} --settings {project_conf}'.format(dj_command=command, **env),
            **kwargs)
