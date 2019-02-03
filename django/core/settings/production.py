# FIXME: probably better to have a common mixin instead of pulling all staging.py settings since this also brings in
# INSTALLED_APPS that we might not want (like fixture_magic which is fairly specialized)
from .staging import *

INSTALLED_APPS = DJANGO_APPS + WAGTAIL_APPS + COMSES_APPS + THIRD_PARTY_APPS

DEBUG = False
DEPLOY_ENVIRONMENT = Environment.PRODUCTION
EMAIL_SUBJECT_PREFIX = config.get('email', 'EMAIL_SUBJECT_PREFIX', fallback='[comses.net]')
# http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
# remove sandbox orcid provider
SOCIALACCOUNT_PROVIDERS.pop('orcid', None)

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'match_extension': '.jinja',
            'newstyle_gettext': True,
            # DEFAULT_EXTENSIONS at https://github.com/niwinz/django-jinja/blob/master/django_jinja/builtins/__init__.py
            "extensions": DEFAULT_EXTENSIONS + [
                "django_jinja.builtins.extensions.DjangoExtraFiltersExtension",
                'wagtail.contrib.settings.jinja2tags.settings',
                'wagtail.core.jinja2tags.core',
                'wagtail.admin.jinja2tags.userbar',
                'wagtail.images.jinja2tags.images',
                'waffle.jinja.WaffleExtension',
            ],
            'constants': {
                'DISCOURSE_BASE_URL': DISCOURSE_BASE_URL
            },
            'auto_reload': False,
            'translation_engine': 'django.utils.translation',
            # FIXME: https://docs.djangoproject.com/en/2.0/topics/templates/#module-django.template.backends.django
            # context_processor usage in jinja templates is discouraged
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'autoescape': True,
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'wagtail.contrib.settings.context_processors.settings',
            ],
        },
    },
]
