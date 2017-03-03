from .defaults import *

DEBUG = False
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# FIXME: remove after successful data migration
INSTALLED_APPS += ['drupal_migrator']

ALLOWED_HOSTS = ['.comses.net']

# TODO: refactor root paths, repository / library / etc
MEDIA_ROOT = '/shared/media'

STATIC_ROOT = '/static'
