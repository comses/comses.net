from .dev import *

LIBRARY_ROOT = 'library/tests/tmp'

LOGGING['loggers']['core.views'] = {
    'level': 'ERROR',
    'handlers': ['console'],
    'propagate': False
}