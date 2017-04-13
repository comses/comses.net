from .defaults import *

DEBUG = False

# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/shared/logs/mail.log'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = config.get('email', 'EMAIL_HOST', fallback='smtp.sparkpostmail.com')
EMAIL_PORT = config.get('email', 'EMAIL_PORT', fallback='587')
EMAIL_HOST_USER = config.get('email', 'EMAIL_HOST_USER', fallback='SMTP_Injection')
EMAIL_HOST_PASSWORD = config.get('email', 'EMAIL_HOST_PASSWORD', fallback='')
EMAIL_SUBJECT_PREFIX = config.get('email', 'EMAIL_SUBJECT_PREFIX', fallback='[comses.net]')
EMAIL_USE_TLS = True

# FIXME: remove after successful data migration
INSTALLED_APPS += ['drupal_migrator']

ALLOWED_HOSTS = ['.comses.net']

# TODO: refactor root paths, repository / library / etc
MEDIA_ROOT = '/shared/media'

STATIC_ROOT = '/shared/static'

WSGI_APPLICATION = 'core.wsgi.application'

