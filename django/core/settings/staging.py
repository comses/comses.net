from .defaults import *

DEBUG = False
DEPLOY_ENVIRONMENT = Environment.STAGING

# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/shared/logs/mail.log'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


EMAIL_HOST = config.get('email', 'EMAIL_HOST', fallback='smtp.sparkpostmail.com')
EMAIL_PORT = config.get('email', 'EMAIL_PORT', fallback='587')
EMAIL_HOST_USER = config.get('email', 'EMAIL_HOST_USER', fallback='SMTP_Injection')
EMAIL_HOST_PASSWORD = config.get('email', 'EMAIL_HOST_PASSWORD', fallback='')
EMAIL_SUBJECT_PREFIX = config.get('email', 'EMAIL_SUBJECT_PREFIX', fallback='[test.comses.net]')
EMAIL_USE_TLS = True

ALLOWED_HOSTS = ['.comses.net']

# see https://docs.sentry.io/clients/python/integrations/django/
# add sentry error id middleware for better tracking
MIDDLEWARE += ['raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware']

WSGI_APPLICATION = 'core.wsgi.application'

INSTALLED_APPS += [
    'raven.contrib.django.raven_compat',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry', 'rollingfile', 'console'],
    },
    'formatters': {
        'verbose': {
            # 'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            'format': '%(asctime)s %(levelname)-7s %(name)s:%(funcName)s:%(lineno)d %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'djangofile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIRECTORY, 'django.log'),
            'backupCount': 6,
            'maxBytes': 10000000,
        },
        'rollingfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIRECTORY, 'comsesnet.log'),
            'backupCount': 6,
            'maxBytes': 10000000,
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['djangofile', 'console'],
            'propagate': False,
        },
        'django': {
            'level': 'DEBUG',
            'handlers': ['console', 'djangofile'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console', 'djangofile'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}
