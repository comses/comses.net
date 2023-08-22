"""
Django and Wagtail settings for the comses.net CMS

Django settings reference:
  https://docs.djangoproject.com/en/4.2/topics/settings/

Wagtail settings reference:
  https://docs.wagtail.org/en/stable/reference/contrib/settings.html

"""

import configparser
import os
from enum import Enum
from pathlib import Path

from django.contrib.messages import constants as messages


class Environment(Enum):
    DEVELOPMENT = "http://localhost:8000"
    STAGING = "https://staging.comses.net"
    PRODUCTION = "https://www.comses.net"
    TEST = "http://localhost:8000"

    @property
    def base_url(self):
        return self.value

    @property
    def is_staging_or_production(self):
        return self in (Environment.PRODUCTION, Environment.STAGING)

    @property
    def is_production(self):
        return self == Environment.PRODUCTION

    @property
    def is_staging(self):
        return self == Environment.STAGING

    @property
    def is_development(self):
        return self == Environment.DEVELOPMENT

    @property
    def is_test(self):
        return self == Environment.TEST


DEPLOY_ENVIRONMENT = Environment.DEVELOPMENT

# go two levels up for root project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# base directory is one level above the project directory
BASE_DIR = os.path.dirname(PROJECT_DIR)

DEBUG = True

DJANGO_VITE_DEV_MODE = True

# Spam detection configuration
SPAM_DIR_PATH = Path("/shared/curator/spam")
SPAM_TRAINING_DATASET_PATH = Path("./curator/spam_dataset.csv")

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
# FIXME: needs to be overridden in staging and prod after updating DEPLOY_ENVIRONMENT which is less than ideal

WAGTAILADMIN_BASE_URL = BASE_URL = DEPLOY_ENVIRONMENT.base_url
# set up robots + sitemaps inclusion https://django-robots.readthedocs.io/en/latest/
ROBOTS_SITEMAP_URLS = [f"{BASE_URL}/sitemap.xml"]

# wagtail config: https://docs.wagtail.io/en/v2.10.1/getting_started/integrating_into_django.html
WAGTAIL_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "wagtail.contrib.modeladmin",
    "wagtail.contrib.settings",
    "wagtail.contrib.search_promotions",
    "taggit",
    "modelcluster",
    "search",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "hcaptcha_field",
    "cookielaw",
    "django_extensions",
    "django_vite",
    "guardian",
    "rest_framework",
    "rest_framework_swagger",
    "robots",
    "timezone_field",
    "waffle",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.orcid",
]

COMSES_APPS = [
    "core.apps.CoreConfig",
    "home.apps.HomeConfig",
    "library.apps.LibraryConfig",
    "curator.apps.CuratorConfig",
]

INSTALLED_APPS = DJANGO_APPS + WAGTAIL_APPS + COMSES_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # allauth account middleware
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
]

AUTHENTICATION_BACKENDS = (
    "allauth.account.auth_backends.AuthenticationBackend",
    "core.backends.ComsesObjectPermissionBackend",
    "guardian.backends.ObjectPermissionBackend",
)

#########################################################
# Content Security Policy support provided via django-csp
#
# https://django-csp.readthedocs.io/en/latest/index.html
#
# Full CSP Spec: https://www.w3.org/TR/CSP/


# basic development settings, override with more paranoid in staging/prod
CSP_DEFAULT_SRC = ("'self'", "localhost:*", "ws:")
CSP_SCRIPT_SRC = (
    "'self'",
    "localhost:*",
    "cdnjs.cloudflare.com",
    "browser.sentry-cdn.com",
    "www.googletagmanager.com",
    "https://*.comses.net",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_CONNECT_SRC = (
    "'self'",
    "localhost:*",
    "ws:",  # websockets
    "api.ror.org",  # RoR affiliations dropdown support
    "cdn.jsdelivr.net",  # codemirror spell checker
    "*.comses.net",  # sentry.comses.net / forum.comses.net
    "www.google-analytics.com",  # google analytics
)
CSP_FONT_SRC = ("'self'", "fonts.googleapis.com", "fonts.gstatic.com", "localhost:*")
CSP_STYLE_SRC = (
    "'self'",
    "cdnjs.cloudflare.com",
    "fonts.googleapis.com",
    "maxcdn.bootstrapcdn.com",  # font awesome fonts
    "localhost:*",
    "'unsafe-inline'",
)
CSP_IMG_SRC = ("'self'", "data:", "localhost:*", "i.ytimg.com")
CSP_FRAME_SRC = (
    "'self'",
    "*.comses.net",
    "youtube.com",
    "*.youtube.com",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_INCLUDE_NONCE_IN = ["script-src"]
CSP_EXCLUDE_URL_PREFIXES = ("/wagtail/admin", "/django/admin")


# Enable the sites framework for Wagtail + django-allauth
SITE_ID = 1

ROOT_URLCONF = "core.urls"

# configure elasticsearch 7 wagtail backend
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.elasticsearch7",
        "URLS": ["http://elasticsearch:9200"],
        "ATOMIC_REBUILD": True,
        "AUTO_UPDATE": True,
        "TIMEOUT": 30,
        "OPTIONS": {
            "max_retries": 2,
        },
        "INDEX_SETTINGS": {},
    }
}

# make tags case insensitive
TAGGIT_CASE_INSENSITIVE = True

# max number of items to include in rss or atom feeds
DEFAULT_FEED_MAX_ITEMS = 120

# admin dashboard defaults
# max number of items to include in each admin dashboard recent activity category
ADMIN_DASHBOARD_MAX_ITEMS = 15
# size of the sliding window to filter recent activity in the admin dashboard
# from now to 90 days ago
ADMIN_DASHBOARD_DAYS = 90

config = configparser.ConfigParser()
# FIXME: switch to docker secrets instead
config.read("/run/secrets/config.ini")

RELEASE_VERSION = config.get("default", "BUILD_ID", fallback="v2023.01")

# default from email for various automated emails sent by Django
DEFAULT_FROM_EMAIL = config.get(
    "email", "DEFAULT_FROM_EMAIL", fallback="info@comses.net"
)
# email address used for errors emails sent to ADMINS and MANAGERS
SERVER_EMAIL = config.get("email", "SERVER_EMAIL", fallback="editors@comses.net")
EDITOR_EMAIL = config.get("email", "EDITOR_EMAIL", fallback="editors@comses.net")
REVIEW_EDITOR_EMAIL = config.get(
    "email", "REVIEW_EDITOR_EMAIL", fallback="reviews@comses.net"
)
# default email subject prefix
EMAIL_SUBJECT_PREFIX = config.get(
    "email", "EMAIL_SUBJECT_PREFIX", fallback="[CoMSES Net]"
)

# number of days before a peer review invitation expires
PEER_REVIEW_INVITATION_EXPIRATION = 21

# RECAPTCHA_PUBLIC_KEY = config.get('captcha', 'RECAPTCHA_PUBLIC_KEY', fallback='')
# RECAPTCHA_PRIVATE_KEY = config.get('captcha', 'RECAPTCHA_PRIVATE_KEY', fallback='')
# NOCAPTCHA = True

# sentry DSN
SENTRY_DSN = config.get(
    "logging", "SENTRY_DSN", fallback="https://sentry.example.com/2"
)

SECRET_KEY = config.get("secrets", "SECRET_KEY")

# regular settings

EXPIRED_JOB_DAYS_THRESHOLD = config.getint(
    "default", "EXPIRED_JOB_DAYS_THRESHOLD", fallback=180
)

EXPIRED_EVENT_DAYS_THRESHOLD = config.getint(
    "default", "EXPIRED_EVENT_DAYS_THRESHOLD", fallback=2
)

# Database configuration
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config.get("database", "DB_NAME"),
        "USER": config.get("database", "DB_USER"),
        "PASSWORD": config.get("database", "DB_PASSWORD"),
        "HOST": config.get("database", "DB_HOST"),
        "PORT": config.get("database", "DB_PORT"),
    }
}

SHARE_DIR = "/shared"
LOG_DIRECTORY = config.get(
    "logging", "LOG_DIRECTORY", fallback=os.path.join(BASE_DIR, "logs")
)
LIBRARY_ROOT = config.get(
    "storage", "LIBRARY_ROOT", fallback=os.path.join(BASE_DIR, "library")
)
PREVIOUS_SHARE_ROOT = os.path.join(SHARE_DIR, ".latest")
REPOSITORY_ROOT = config.get(
    "storage", "REPOSITORY_ROOT", fallback=os.path.join(BASE_DIR, "repository")
)
BORG_ROOT = "/shared/backups/repo"
BACKUP_ROOT = "/shared/backups"
EXTRACT_ROOT = "/shared/extract"

FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_TEMP_DIR = "/shared/uploads/"

for d in (LOG_DIRECTORY, LIBRARY_ROOT, REPOSITORY_ROOT, FILE_UPLOAD_TEMP_DIR):
    try:
        if not os.path.isdir(d):
            os.mkdir(d)
    except OSError:
        print("Unable to create directory", d)

# simple dev logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {
        "level": "INFO",
        "handlers": ["console", "comsesfile"],
    },
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)-7s %(name)s:%(funcName)s:%(lineno)d %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "verbose",
        },
        "djangofile": {
            "level": "DEBUG",
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIRECTORY, "django.log"),
        },
        "comsesfile": {
            "level": "DEBUG",
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIRECTORY, "comsesnet.log"),
        },
    },
    "loggers": {
        "bagit": {
            "level": "WARNING",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "django": {
            "level": "WARNING",
            "handlers": ["djangofile"],
            "propagate": False,
        },
        "home": {
            "level": "DEBUG",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "library": {
            "level": "DEBUG",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "core": {
            "level": "DEBUG",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "invoke": {
            "level": "INFO",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "MARKDOWN": {
            "level": "ERROR",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "breadability": {
            "level": "ERROR",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# django-vite settings
DJANGO_VITE_ASSETS_PATH = config.get("storage", "VITE_ROOT", fallback="/shared/vite")
DJANGO_VITE_STATIC_URL_PREFIX = "bundles"
DJANGO_VITE_DEV_SERVER_PORT = 5000
DJANG_VITE_MANIFEST_PATH = os.path.join(
    DJANGO_VITE_ASSETS_PATH, DJANGO_VITE_STATIC_URL_PREFIX, "manifest.json"
)

STATIC_ROOT = "/shared/static"
STATIC_URL = "/static/"

STATICFILES_DIRS = [DJANGO_VITE_ASSETS_PATH]

MEDIA_ROOT = "/shared/media"
MEDIA_URL = "/media/"
APPEND_SLASH = True

# Wagtail specific settings

WAGTAIL_SITE_NAME = "CoMSES Net"
WAGTAIL_APPEND_SLASH = True
WAGTAIL_GRAVATAR_PROVIDER_URL = None

# authentication settings
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
WAGTAIL_FRONTEND_LOGIN_URL = "account_login"


REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.DjangoObjectPermissions",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "core.renderers.RootContextHTMLRenderer",
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "EXCEPTION_HANDLER": "core.views.rest_exception_handler",
    "PAGE_SIZE": 10,
}

# add redis cache http://docs.wagtail.io/en/v2.8/advanced_topics/performance.html#cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # FIXME: switch to TCP in prod
        "LOCATION": "unix:///shared/redis/redis.sock",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# SSO, user registration, and django-allauth configuration, see
# https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_ADAPTER = 'core.adapter.AccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 15
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FORM_CLASS = "core.forms.SignupForm"
# FIXME: enable after configuring form
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = True
ACCOUNT_TEMPLATE_EXTENSION = "jinja"
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# allow django-allauth to change emails
ACCOUNT_CHANGE_EMAIL = True

ORCID_CLIENT_ID = config.get("secrets", "ORCID_CLIENT_ID", fallback="")
ORCID_CLIENT_SECRET = config.get("secrets", "ORCID_CLIENT_SECRET", fallback="")

GITHUB_CLIENT_ID = config.get("secrets", "GITHUB_CLIENT_ID", fallback="")
GITHUB_CLIENT_SECRET = config.get("secrets", "GITHUB_CLIENT_SECRET", fallback="")

TEST_BASIC_AUTH_PASSWORD = config.get(
    "test", "TEST_BASIC_AUTH_PASSWORD", fallback="test password"
)
TEST_USER_ID = config.get("test", "TEST_USER_ID", fallback=1000000)
TEST_USERNAME = config.get("test", "TEST_USERNAME", fallback="__test_user__")

SOCIALACCOUNT_PROVIDERS = {
    # https://developer.github.com/apps/building-integrations/setting-up-and-registering-oauth-apps/about-scopes-for-oauth-apps/
    "github": {
        "SCOPE": [
            "user:email",
            "read:org",
        ],
    },
    # http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
    # NOTE: must be deleted in production settings
    "orcid": {
        "BASE_DOMAIN": "sandbox.orcid.org",
        "MEMBER_API": True,
    },
}


DISCOURSE_BASE_URL = config.get(
    "discourse", "DISCOURSE_BASE_URL", fallback="https://staging-discourse.comses.net"
)
DISCOURSE_SSO_SECRET = config.get(
    "secrets", "DISCOURSE_SSO_SECRET", fallback="unconfigured"
)
DISCOURSE_API_KEY = config.get("secrets", "DISCOURSE_API_KEY", fallback="unconfigured")
DISCOURSE_API_USERNAME = config.get(
    "discourse", "DISCOURSE_API_USERNAME", fallback="unconfigured"
)

# https://docs.djangoproject.com/en/4.2/ref/settings/#templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "APP_DIRS": True,
        "OPTIONS": {
            "extensions": [
                "core.jinja2ext.ViteExtension",
                "wagtail.contrib.settings.jinja2tags.settings",
                "wagtail.jinja2tags.core",
                "wagtail.admin.jinja2tags.userbar",
                "wagtail.images.jinja2tags.images",
                "csp.extensions.NoncedScript",
                "waffle.jinja.WaffleExtension",
            ],
            "environment": "core.jinja_config.environment",
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "csp.context_processors.nonce",
                "wagtail.contrib.settings.context_processors.settings",
            ],
            "libraries": {
                "csp": "csp.templatetags.csp",
            },
        },
    },
]

MESSAGE_TAGS = {
    messages.SUCCESS: "alert alert-success",
    messages.DEBUG: "alert alert-info",
    messages.INFO: "alert alert-info",
    messages.WARNING: "alert alert-warning",
    messages.ERROR: "alert alert-danger",
}

ACCEPTED_IMAGE_TYPES = ["gif", "jpeg", "png"]
