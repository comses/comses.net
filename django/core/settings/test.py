from os import path

from .defaults import *

DEPLOY_ENVIRONMENT, WAGTAILADMIN_BASE_URL, BASE_URL = set_environment(Environment.TEST)
TESTING = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "server"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["loggers"]["core.views"] = {
    "level": "ERROR",
    "handlers": ["console"],
    "propagate": False,
}

SHARE_DIR = path.realpath("/shared/tests")
LIBRARY_ROOT = path.join(SHARE_DIR, "library")
LIBRARY_PREVIOUS_ROOT = path.join(SHARE_DIR, ".latest")
REPOSITORY_ROOT = path.join(SHARE_DIR, "repository")
BACKUP_ROOT = path.join(SHARE_DIR, "backups")
BORG_ROOT = path.join(BACKUP_ROOT, "repo")
EXTRACT_ROOT = path.join(SHARE_DIR, "extract")
MEDIA_ROOT = path.join(SHARE_DIR, "media")

DATABASES["dump_restore"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "dump_restore_{}".format(os.getenv("DB_NAME")),
    "USER": os.getenv("DB_USER"),
    "PASSWORD": os.getenv("DB_PASSWORD"),
    "HOST": os.getenv("DB_HOST"),
    "PORT": os.getenv("DB_PORT"),
}


DATABASE_ROUTERS = [
    "core.database_routers.DumpRestoreRouter",
    "core.database_routers.DefaultRouter",
]
