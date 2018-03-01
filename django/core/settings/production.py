from .staging import *

DEBUG = False
DEPLOY_ENVIRONMENT = Environment.PRODUCTION
EMAIL_SUBJECT_PREFIX = config.get('email', 'EMAIL_SUBJECT_PREFIX', fallback='[comses.net]')
# http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
# remove sandbox orcid provider
SOCIALACCOUNT_PROVIDERS.pop('orcid', None)


