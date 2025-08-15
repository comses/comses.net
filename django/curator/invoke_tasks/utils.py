import logging
import os

logger = logging.getLogger(__name__)


env = {
    "python": "python3",
    "project_name": "cms",
    "project_conf": os.environ.get("DJANGO_SETTINGS_MODULE"),
    "coverage_omit_patterns": (
        "templates/*",
        "settings/*",
        "migrations/*",
        "wsgi.py",
        "management/*",
        "tasks.py",
        "apps.py",
    ),
    "coverage_src_patterns": (
        "home",
        "library",
        "core",
    ),
}


def dj(ctx, command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    django_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    invocation = (
        f"python3 /code/manage.py {command} --settings {django_settings_module}"
    )
    print("Invoking command: ", invocation)
    ctx.run(
        invocation, env={"DJANGO_SETTINGS_MODULE": django_settings_module}, **kwargs
    )
