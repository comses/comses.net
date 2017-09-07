from .defaults import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INSTALLED_APPS += ['drupal_migrator', 'debug_toolbar']

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'dev.comses.asu.edu']
