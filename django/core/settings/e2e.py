from .test import *

DEBUG = True

DJANGO_VITE_DEV_MODE = False

SHARE_DIR = path.realpath("/shared/e2e")
LIBRARY_ROOT = path.join(SHARE_DIR, "library")
LIBRARY_PREVIOUS_ROOT = path.join(SHARE_DIR, ".latest")
REPOSITORY_ROOT = path.join(SHARE_DIR, "repository")
BACKUP_ROOT = path.join(SHARE_DIR, "backups")
BORG_ROOT = path.join(BACKUP_ROOT, "repo")
EXTRACT_ROOT = path.join(SHARE_DIR, "extract")
MEDIA_ROOT = path.join(SHARE_DIR, "media")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": read_secret("db_password", os.getenv("DB_PASSWORD")),
        "HOST": "e2edb",
        "PORT": os.getenv("DB_PORT"),
    }
}
