"""
Django settings for core.comses.net

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import configparser
import os
import pathlib
from enum import Enum

from django_jinja.builtins import DEFAULT_EXTENSIONS
from django.contrib.messages import constants as messages


class Environment(Enum):
    DEVELOPMENT = 0
    STAGING = 1
    PRODUCTION = 2
    TEST = 3

    def is_staging_or_production(self):
        return self in (Environment.PRODUCTION, Environment.STAGING)

    def is_production(self):
        return self == Environment.PRODUCTION

    def is_staging(self):
        return self == Environment.STAGING

    def is_development(self):
        return self == Environment.DEVELOPMENT

    def is_test(self):
        return self == Environment.TEST


DEPLOY_ENVIRONMENT = Environment.DEVELOPMENT

# go two levels up for root project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# base directory is one level above the project directory
BASE_DIR = os.path.dirname(PROJECT_DIR)

DEBUG = True

# Quick-start development settings - make sure to properly override in prod.py
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# wagtail configuration: http://docs.wagtail.io/en/v2.0.1/getting_started/integrating_into_django.html
WAGTAIL_APPS = [
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail.core',
    'wagtail.contrib.modeladmin',
    'wagtail.contrib.settings',
    'taggit',
    'modelcluster',
    'search',
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'captcha',
    'cookielaw',
    'django_extensions',
    'django_jinja',
    'guardian',
    'rest_framework',
    'rest_framework_swagger',
    'robots',
    'timezone_field',
    'webpack_loader',
    'waffle',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.orcid',
]

COMSES_APPS = [
    'core.apps.CoreConfig',
    'home.apps.HomeConfig',
    'library.apps.LibraryConfig',
    'curator.apps.CuratorConfig',
    'conference.apps.ConferenceConfig',
]

INSTALLED_APPS = DJANGO_APPS + WAGTAIL_APPS + COMSES_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'waffle.middleware.WaffleMiddleware',
    'wagtail.core.middleware.SiteMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'allauth.account.auth_backends.AuthenticationBackend',
    'core.backends.ComsesObjectPermissionBackend',
    'guardian.backends.ObjectPermissionBackend'
)

# Enable the sites framework for Wagtail + django-allauth
SITE_ID = 1

ROOT_URLCONF = 'core.urls'

# configure elasticsearch 5 wagtail backend
WAGTAILSEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'wagtail.search.backends.elasticsearch5',
        'URLS': ['http://elasticsearch:9200'],
        'INDEX': 'wagtail',
        # 'ATOMIC_REBUILD': True,
        'AUTO_UPDATE': False,
        'TIMEOUT': 10,
        'OPTIONS': {
            'max_retries': 2,
        },
        'INDEX_SETTINGS': {}
    }
}

# make tags case insensitive
TAGGIT_CASE_INSENSITIVE = True

RELEASE_VERSION_FILE = "release-version.txt"

release_version_file = pathlib.Path(RELEASE_VERSION_FILE)
RELEASE_VERSION = "v1.0.6"

if release_version_file.is_file():
    with release_version_file.open('r') as infile:
        RELEASE_VERSION = infile.read().strip()

config = configparser.ConfigParser()
# FIXME: switch to docker secrets instead
IS_IN_DOCKER = os.path.exists('/secrets/config.ini')
# FIXME: set up better shared paths
if IS_IN_DOCKER:
    config.read('/secrets/config.ini')
else:
    config.read('../deploy/conf/config.ini.debug')

# default from email for various automated emails sent by Django
DEFAULT_FROM_EMAIL = config.get('email', 'DEFAULT_FROM_EMAIL', fallback='info@comses.net')
# email address used for errors emails sent to ADMINS and MANAGERS
SERVER_EMAIL = config.get('email', 'SERVER_EMAIL', fallback='editors@comses.net')

RECAPTCHA_PUBLIC_KEY = config.get('captcha', 'RECAPTCHA_PUBLIC_KEY', fallback='')
RECAPTCHA_PRIVATE_KEY = config.get('captcha', 'RECAPTCHA_PRIVATE_KEY', fallback='')
NOCAPTCHA = True

RAVEN_CONFIG = {
    'dsn': config.get('logging', 'SENTRY_DSN', fallback=''),
    'public_dsn': config.get('logging', 'SENTRY_PUBLIC_DSN', fallback=''),
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    # 'release': raven.fetch_git_sha(BASE_DIR),
}


SECRET_KEY = config.get('secrets', 'SECRET_KEY')

# Database configuration
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config.get('database', 'DB_NAME'),
        'USER': config.get('database', 'DB_USER'),
        'PASSWORD': config.get('database', 'DB_PASSWORD'),
        'HOST': config.get('database', 'DB_HOST'),
        'PORT': config.get('database', 'DB_PORT'),
    }
}

SHARE_DIR = '/shared'
LOG_DIRECTORY = config.get('logging', 'LOG_DIRECTORY', fallback=os.path.join(BASE_DIR, 'logs'))
LIBRARY_ROOT = config.get('storage', 'LIBRARY_ROOT', fallback=os.path.join(BASE_DIR, 'library'))
PREVIOUS_SHARE_ROOT = os.path.join(SHARE_DIR, '.latest')
REPOSITORY_ROOT = config.get('storage', 'REPOSITORY_ROOT', fallback=os.path.join(BASE_DIR, 'repository'))
BORG_ROOT = '/shared/backups/repo'
BACKUP_ROOT = '/shared/backups'
EXTRACT_ROOT = '/shared/extract'


for d in (LOG_DIRECTORY, LIBRARY_ROOT, REPOSITORY_ROOT):
    try:
        if not os.path.isdir(d):
            os.mkdir(d)
    except OSError:
        print("Unable to create directory", d)

# simple dev logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'rollingfile'],
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)-7s %(name)s:%(funcName)s:%(lineno)d %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
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
        'bagit': {
            'level': 'WARNING',
            'handlers': ['console', 'rollingfile'],
            'propagate': False
        },
        'django': {
            'level': 'WARNING',
            'handlers': ['djangofile'],
            'propagate': False,
        },
        'home': {
            'level': 'DEBUG',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
        'library': {
            'level': 'DEBUG',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
        'core': {
            'level': 'DEBUG',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
        'invoke': {
            'level': 'INFO',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
        'MARKDOWN': {
            'level': 'ERROR',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
        'breadability': {
            'level': 'ERROR',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
    }
}

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

WEBPACK_DIR = config.get('storage', 'WEBPACK_ROOT', fallback='/shared/webpack')

STATICFILES_DIRS = [
    WEBPACK_DIR
]

STATIC_ROOT = '/shared/static'
STATIC_URL = '/static/'

MEDIA_ROOT = '/shared/media'
MEDIA_URL = '/media/'

# Wagtail settings

WAGTAIL_SITE_NAME = "CoMSES Net"
APPEND_SLASH = True
WAGTAIL_APPEND_SLASH = True

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'assets/',
        'STATS_FILE': os.path.join(WEBPACK_DIR, 'webpack-stats.json'),
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
BASE_URL = 'https://www.comses.net'

# authentication settings
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
WAGTAIL_FRONTEND_LOGIN_URL = 'auth_login'


REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.DjangoObjectPermissions',),
    'DEFAULT_RENDERER_CLASSES': (
        'core.renderers.RootContextHTMLRenderer',
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    'EXCEPTION_HANDLER': 'core.views.rest_exception_handler',
    'PAGE_SIZE': 10
}

# add redis cache http://docs.wagtail.io/en/v2.0.1/advanced_topics/performance.html#cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # FIXME: switch to TCP in prod
        'LOCATION': 'unix:/shared/redis/redis.sock',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# SSO, user registration, and django-allauth configuration, see
# https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_ADAPTER = 'core.adapter.AccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 15
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FORM_CLASS = 'core.forms.SignupForm'
ACCOUNT_TEMPLATE_EXTENSION = 'jinja'
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

ORCID_CLIENT_ID = config.get('secrets', 'ORCID_CLIENT_ID', fallback='')
ORCID_CLIENT_SECRET = config.get('secrets', 'ORCID_CLIENT_SECRET', fallback='')

GITHUB_CLIENT_ID = config.get('secrets', 'GITHUB_CLIENT_ID', fallback='')
GITHUB_CLIENT_SECRET = config.get('secrets', 'GITHUB_CLIENT_SECRET', fallback='')

TEST_BASIC_AUTH_PASSWORD = config.get('test', 'TEST_BASIC_AUTH_PASSWORD', fallback='test password')
TEST_USER_ID = config.get('test', 'TEST_USER_ID', fallback=1000000)
TEST_USERNAME = config.get('test', 'TEST_USERNAME', fallback='__test_user__')

SOCIALACCOUNT_PROVIDERS = {
    # https://developer.github.com/apps/building-integrations/setting-up-and-registering-oauth-apps/about-scopes-for-oauth-apps/
    'github': {
        'SCOPE': [
            'user:email',
            'read:org',
        ],
    },
    # http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
    # NOTE: must be deleted in production settings
    'orcid': {
        'BASE_DOMAIN': 'sandbox.orcid.org',
        'MEMBER_API': True,
    },
}

DISCOURSE_BASE_URL = config.get('discourse', 'DISCOURSE_BASE_URL', fallback='https://test-discourse.comses.net')
DISCOURSE_SSO_SECRET = config.get('secrets', 'DISCOURSE_SSO_SECRET', fallback='unconfigured')
DISCOURSE_API_KEY = config.get('secrets', 'DISCOURSE_API_KEY', fallback='unconfigured')
DISCOURSE_API_USERNAME = config.get('discourse', 'DISCOURSE_API_USERNAME', fallback='unconfigured')

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
            'auto_reload': True,
            'translation_engine': 'django.utils.translation',
            # FIXME: https://docs.djangoproject.com/en/2.0/topics/templates/#module-django.template.backends.django
            # context_processor usage in jinja templates is discouraged, move these over eventually
            'context_processors': [
                'django.template.context_processors.debug',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'wagtail.contrib.settings.context_processors.settings',
            ],
        },
    },
]

MESSAGE_TAGS = {
    messages.SUCCESS: 'alert alert-success',
    messages.DEBUG: '',
    messages.INFO: 'alert alert-info',
    messages.WARNING: 'alert alert-warning',
    messages.ERROR: 'alert alert-danger'
}
