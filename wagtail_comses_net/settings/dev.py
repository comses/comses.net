from __future__ import absolute_import, unicode_literals
from logging import Formatter
from datetime import time

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

class VerboseFormatter(Formatter):
    def format(self, record):
        name_funcName_line = '{}:{}:{}'.format(record.name, record.funcName, record.lineno)
        asctime = time.strftime(self.datefmt)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)-7s %(name)s:%(funcName)s:%(lineno)d %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': "%(levelname)-8s %(message)s"
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'home': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        }
    }
}

try:
    from .local import *
except ImportError:
    pass
