"""
Django settings for core.comses.net

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

from django_jinja.builtins import DEFAULT_EXTENSIONS

import configparser
import os

# go two levels up for root project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# base directory is one level above the project directory
BASE_DIR = os.path.dirname(PROJECT_DIR)

DEBUG = True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# Application definition
WAGTAIL_APPS = [
    'wagtail.wagtailforms',
    'wagtail.wagtailredirects',
    'wagtail.wagtailembeds',
    'wagtail.wagtailsites',
    'wagtail.wagtailusers',
    'wagtail.wagtailsnippets',
    'wagtail.wagtaildocs',
    'wagtail.wagtailimages',
    'wagtail.wagtailsearch',
    'wagtail.wagtailadmin',
    'wagtail.wagtailcore',
    'wagtail.contrib.modeladmin',
    'wagtail.contrib.settings',
    'wagtailmenus',
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
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'django_extensions',
    'django_jinja',
    'guardian',
    'rest_framework',
    'rest_framework_swagger',
    'timezone_field',
    'webpack_loader',
    # django-allauth setup
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.orcid',
]

COMSES_APPS = [
    'core.apps.CoreConfig',
    'citation.apps.CitationConfig',
    'home.apps.HomeConfig',
    'library.apps.LibraryConfig',
]

INSTALLED_APPS = DJANGO_APPS + WAGTAIL_APPS + COMSES_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'wagtail.wagtailcore.middleware.SiteMiddleware',
    'wagtail.wagtailredirects.middleware.RedirectMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'core.backends.EmailAuthenticationBackend',
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
        'BACKEND': 'wagtail.wagtailsearch.backends.elasticsearch5',
        'URLS': ['http://elasticsearch:9200'],
        'INDEX': 'wagtail',
        'ATOMIC_REBUILD': True,
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

config = configparser.ConfigParser()

# default from email for various automated emails sent by Django
DEFAULT_FROM_EMAIL = config.get('email', 'DEFAULT_FROM_EMAIL', fallback='info@comses.net')
# email address used for errors emails sent to ADMINS and MANAGERS
SERVER_EMAIL = config.get('email', 'SERVER_EMAIL', fallback='admin@comses.net')

IS_IN_DOCKER = os.path.exists('/secrets/config.ini')

# FIXME: set up better shared paths
if IS_IN_DOCKER:
    config.read('/secrets/config.ini')
else:
    config.read('../deploy/conf/config.ini.debug')

SECRET_KEY = config.get('secrets', 'SECRET_KEY')

# Database configuration
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

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

LOG_DIRECTORY = config.get('logging', 'LOG_DIRECTORY', fallback=os.path.join(BASE_DIR, 'logs'))
LIBRARY_ROOT = config.get('storage', 'LIBRARY_ROOT', fallback=os.path.join(BASE_DIR, 'library'))
REPOSITORY_ROOT = config.get('storage', 'REPOSITORY_ROOT', fallback=os.path.join(BASE_DIR, 'repository'))

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
        'drupal_migrator': {
            'level': 'DEBUG',
            'handlers': ['console', 'rollingfile'],
            'propagate': False,
        },
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

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

WAGTAIL_SITE_NAME = "CoMSES Network"
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

WAGTAILMENUS_DEFAULT_MAIN_MENU_TEMPLATE = 'home/includes/menu.html'

# authentication settings
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
WAGTAIL_FRONTEND_LOGIN_URL = 'auth_login'


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('core.permissions.ComsesPermissions',),
    'DEFAULT_RENDERER_CLASSES': (
        'core.renderers.RootContextHTMLRenderer',
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    'PAGE_SIZE': 10
}

# add redis cache http://docs.wagtail.io/en/v1.10.1/advanced_topics/performance.html#cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
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
ACCOUNT_SIGNUP_FORM_CLASS = 'home.forms.SignupForm'
ACCOUNT_TEMPLATE_EXTENSION = 'jinja'
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

ORCID_CLIENT_ID = config.get('secrets', 'ORCID_CLIENT_ID', fallback='')
ORCID_CLIENT_SECRET = config.get('secrets', 'ORCID_CLIENT_SECRET', fallback='')

GITHUB_CLIENT_ID = config.get('secrets', 'GITHUB_CLIENT_ID', fallback='')
GITHUB_CLIENT_SECRET = config.get('secrets', 'GITHUB_CLIENT_SECRET', fallback='')

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': [
            'user',
            'repo',
            'read:org',
        ],
    },
    'orcid': {
        'BASE_DOMAIN': 'sandbox.orcid.org',
        'MEMBER_API': True,
    },
}

DISCOURSE_BASE_URL = config.get('discourse', 'DISCOURSE_BASE_URL', fallback='https://forum.comses.net')
DISCOURSE_SSO_SECRET = config.get('secrets', 'DISCOURSE_SSO_SECRET')

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
                'wagtail.wagtailcore.jinja2tags.core',
                'wagtail.wagtailadmin.jinja2tags.userbar',
                'wagtail.wagtailimages.jinja2tags.images',
            ],
            'constants': {
                'DISCOURSE_BASE_URL': DISCOURSE_BASE_URL
            },
            'auto_reload': True,  # FIXME: disable this in production
            'translation_engine': 'django.utils.translation',
            'context_processors': [
                # FIXME: remove debug context processor in production
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'wagtail.contrib.settings.context_processors.settings',
                'wagtailmenus.context_processors.wagtailmenus',
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
                'wagtailmenus.context_processors.wagtailmenus',
            ],
        },
    },
]
