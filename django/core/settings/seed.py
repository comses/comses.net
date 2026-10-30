"""Offline synthetic-seed construction; mount only disposable storage."""

import os
import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

_seed_database = os.environ.get("COMSES_SEED_DATABASE", "")
_seed_root = os.environ.get("COMSES_SEED_ROOT", "")
if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", _seed_database) or _seed_database in {
    "postgres",
    "template0",
    "template1",
}:
    raise ImproperlyConfigured("COMSES_SEED_DATABASE must name an explicit disposable application database.")
if not re.fullmatch(r"/shared/seeds/[a-z0-9_-]+", _seed_root):
    raise ImproperlyConfigured("COMSES_SEED_ROOT must be /shared/seeds/<candidate-name>.")

from .recovery import *  # noqa: E402,F403

# Historical production content migrations assume an existing CMS. A synthetic
# database follows the fresh test-schema path while retaining recovery isolation.
DEPLOY_ENVIRONMENT = Environment.TEST  # noqa: F405
DATABASES = {"default": {**DATABASES["default"], "NAME": _seed_database}}  # noqa: F405
SHARE_DIR = _seed_root
LIBRARY_ROOT = str(Path(SHARE_DIR) / "library")
MEDIA_ROOT = str(Path(SHARE_DIR) / "media")
REPOSITORY_ROOT = str(Path(SHARE_DIR) / "repository")
BACKUP_ROOT = str(Path(SHARE_DIR) / "backups")
BORG_ROOT = str(Path(BACKUP_ROOT) / "repo")
EXTRACT_ROOT = str(Path(SHARE_DIR) / "extract")
PREVIOUS_SHARE_ROOT = str(Path(SHARE_DIR) / ".latest")
FILE_UPLOAD_TEMP_DIR = str(Path(SHARE_DIR) / "uploads")
# Deferred tasks are neither executed nor sent to a persistent/shared queue.
HUEY = {"name": "synthetic-seed", "huey_class": "huey.MemoryHuey", "immediate": False}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database", "AUTO_UPDATE": False}}
