"""
Django and Wagtail settings for the comses.net CMS

Django settings reference:
  https://docs.djangoproject.com/en/4.2/topics/settings/

Wagtail settings reference:
  https://docs.wagtail.org/en/stable/reference/contrib/settings.html

"""

import os
import sys
import warnings
from elasticsearch.exceptions import ElasticsearchWarning
from collections import namedtuple
from enum import Enum
from pathlib import Path

from django.contrib.messages import constants as messages


def read_secret(file, fallback=""):
    secrets_file_path = Path("/run/secrets", file)
    if secrets_file_path.is_file():
        return secrets_file_path.read_text().strip()
    else:
        return fallback


EnvConfig = namedtuple("EnvConfig", ["base_url", "label"])


class Environment(Enum):
    DEVELOPMENT = EnvConfig(base_url="http://localhost:8000", label="DEVELOPMENT")
    STAGING = EnvConfig(base_url="https://staging.comses.net", label="STAGING")
    PRODUCTION = EnvConfig(base_url="https://www.comses.net", label="PRODUCTION")
    # TEST is used for local and github testing, not a real environment
    TEST = EnvConfig(base_url="http://localhost:8000", label="TEST")

    @property
    def base_url(self):
        return self.value.base_url

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


def set_environment(env: Environment):
    global DEPLOY_ENVIRONMENT, WAGTAILADMIN_BASE_URL, BASE_URL
    DEPLOY_ENVIRONMENT = env
    # Base URL to use when referring to full URLs within the Wagtail admin backend -
    # e.g. in notification emails. Don't include '/admin' or a trailing slash
    WAGTAILADMIN_BASE_URL = BASE_URL = env.base_url
    return DEPLOY_ENVIRONMENT, WAGTAILADMIN_BASE_URL, BASE_URL


# go two levels up for root project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# base directory is one level above the project directory
BASE_DIR = os.path.dirname(PROJECT_DIR)

# default to datacite sandbox and test mode
DATACITE_PREFIX = "10.82853"
DATACITE_TEST_MODE = True

DEBUG = True

DJANGO_VITE_DEV_MODE = True


TESTING = "test" in sys.argv or "PYTEST_VERSION" in os.environ

# set up robots + sitemaps inclusion https://django-robots.readthedocs.io/en/latest/
# ROBOTS_SITEMAP_URLS = [f"{BASE_URL}/sitemap.xml"]

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
    "wagtail.contrib.settings",
    "wagtail.contrib.search_promotions",
    "wagtail_modeladmin",
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
    "huey.contrib.djhuey",
    "rest_framework",
    "rest_framework_swagger",
    "robots",
    "timezone_field",
    "waffle",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.google",
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

### configure wagtailmarkdown https://github.com/torchbox/wagtail-markdown

# WAGTAILMARKDOWN = {
#     "autodownload_fontawesome": False,
#     "tab_length": 4,
# }

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
    "export.highcharts.com",  # highcharts metrics export
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

# tune down elasticsearch complaints
warnings.simplefilter("ignore", category=ElasticsearchWarning)

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
        "INDEX_SETTINGS": {"settings": {"index": {"max_result_window": 2500}}},
    }
}

# make tags case insensitive
TAGGIT_CASE_INSENSITIVE = True

# max number of items to include in rss or atom feeds
DEFAULT_FEED_MAX_ITEMS = 120

# max number of items to include in each homepage feed
DEFAULT_HOMEPAGE_FEED_MAX_ITEMS = 5

# admin dashboard defaults
# max number of items to include in each admin dashboard recent activity category
ADMIN_DASHBOARD_MAX_ITEMS = 15
# size of the sliding window to filter recent activity in the admin dashboard
# from now to 90 days ago
ADMIN_DASHBOARD_DAYS = 90

RELEASE_VERSION = os.getenv("RELEASE_VERSION", "v2024.01")

# default from email for various automated emails sent by Django
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "info@comses.net")
# email address used for errors emails sent to ADMINS and MANAGERS
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "editors@comses.net")
EDITOR_EMAIL = os.getenv("EDITOR_EMAIL", "editors@comses.net")
REVIEW_EDITOR_EMAIL = os.getenv("REVIEW_EDITOR_EMAIL", "reviews@comses.net")
# default email subject prefix
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[CoMSES Net]")

# number of days before a peer review invitation expires
PEER_REVIEW_INVITATION_EXPIRATION = 21

# RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY', '')
# RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', '')
# NOCAPTCHA = True

# sentry DSN
SENTRY_DSN = os.getenv("SENTRY_DSN", "https://sentry.example.com/2")
SECRET_KEY = read_secret("django_secret_key", os.getenv("SECRET_KEY"))

# regular settings

EXPIRED_JOB_DAYS_THRESHOLD = int(os.getenv("EXPIRED_JOB_DAYS_THRESHOLD", 180))
EXPIRED_EVENT_DAYS_THRESHOLD = int(os.getenv("EXPIRED_EVENT_DAYS_THRESHOLD", 2))

# number of seconds between the load time and submit time of a form
# submission that is considered likely spam
SPAM_LIKELY_SECONDS_THRESHOLD = 3

# Database configuration
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": read_secret("db_password", os.getenv("DB_PASSWORD")),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

# FIXME: turn everything here into pathlib.Paths at some point
SHARE_DIR = "/shared"
LOG_DIRECTORY = os.path.join(SHARE_DIR, "logs")
LIBRARY_ROOT = os.path.join(SHARE_DIR, "library")
PREVIOUS_SHARE_ROOT = os.path.join(SHARE_DIR, ".latest")
REPOSITORY_ROOT = os.path.join(SHARE_DIR, "repository")
BORG_ROOT = os.path.join(SHARE_DIR, "backups", "repo")
BACKUP_ROOT = os.path.join(SHARE_DIR, "backups")
EXTRACT_ROOT = os.path.join(SHARE_DIR, "extract")

FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_TEMP_DIR = os.path.join(SHARE_DIR, "uploads")

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
        "elasticsearch": {
            "level": "ERROR",
            "handlers": ["console", "comsesfile"],
            "propagate": False,
        },
        "huey": {
            "level": "INFO",
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
DJANGO_VITE_ASSETS_PATH = os.path.join(SHARE_DIR, "vite")
DJANGO_VITE_STATIC_URL_PREFIX = "bundles"
DJANGO_VITE_DEV_SERVER_PORT = 5173
DJANGO_VITE_MANIFEST_PATH = os.path.join(
    DJANGO_VITE_ASSETS_PATH, DJANGO_VITE_STATIC_URL_PREFIX, "manifest.json"
)

STATIC_ROOT = os.path.join(SHARE_DIR, "static")
STATIC_URL = "/static/"

STATICFILES_DIRS = [DJANGO_VITE_ASSETS_PATH]

MEDIA_ROOT = os.path.join(SHARE_DIR, "media")
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
            "CONNECTION_POOL_KWARGS": {"max_connections": 20},
        },
    }
}

HUEY = {
    "name": "comses",
    "huey_class": "core.huey.DjangoRedisHuey",
    "immediate": False,  # always run tasks in the background (for now), if removed it will default to DEBUG
    # FIXME: this should generally be True in development, the huey consumer WILL NOT
    # automatically reload when the code changes when False
}

# SSO, user registration, and django-allauth configuration, see
# https://django-allauth.readthedocs.io/en/latest/installation/quickstart.html
# and
# https://django-allauth.readthedocs.io/en/latest/account/configuration.html
# ACCOUNT_ADAPTER = 'core.adapter.AccountAdapter'
# ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 15
# FIXME: deprecated
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = True
ACCOUNT_SIGNUP_FIELDS = ['email*', 'email2*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FORM_CLASS = "core.forms.SignupForm"
ACCOUNT_TEMPLATE_EXTENSION = "jinja"
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# allow django-allauth to change emails
ACCOUNT_CHANGE_EMAIL = True

ORCID_CLIENT_ID = os.getenv("ORCID_CLIENT_ID", "")
ORCID_CLIENT_SECRET = read_secret("orcid_client_secret")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = read_secret("github_client_secret")

GITHUB_INTEGRATION_APP_ID = int(os.getenv("GITHUB_INTEGRATION_APP_ID") or 0)
GITHUB_INTEGRATION_APP_NAME = os.getenv("GITHUB_INTEGRATION_APP_NAME", "")
GITHUB_INTEGRATION_APP_PRIVATE_KEY = read_secret("github_integration_app_private_key")
GITHUB_INTEGRATION_APP_INSTALLATION_ID = int(
    os.getenv("GITHUB_INTEGRATION_APP_INSTALLATION_ID") or 0
)
GITHUB_INTEGRATION_APP_WEBHOOK_SECRET = read_secret("github_integration_app_webhook_secret")
GITHUB_MODEL_LIBRARY_ORG_NAME = os.getenv("GITHUB_MODEL_LIBRARY_ORG_NAME", "")
GITHUB_INDIVIDUAL_FILE_SIZE_LIMIT = os.getenv(
    "GITHUB_INDIVIDUAL_FILE_SIZE_LIMIT", 100 * 1024 * 1024
)

TEST_BASIC_AUTH_PASSWORD = os.getenv("TEST_BASIC_AUTH_PASSWORD", "test password")
TEST_USER_ID = os.getenv("TEST_USER_ID", 1000000)
TEST_USERNAME = os.getenv("TEST_USERNAME", "__test_user__")

DATACITE_API_USERNAME = os.getenv("DATACITE_API_USERNAME", "comses")
DATACITE_DRY_RUN = os.getenv("DATACITE_DRY_RUN", "true")
DATACITE_API_PASSWORD = read_secret("datacite_api_password")

ROR_API_URL = "https://api.ror.org/v2/organizations"


SOCIALACCOUNT_PROVIDERS = {
    # https://developer.github.com/apps/building-integrations/setting-up-and-registering-oauth-apps/about-scopes-for-oauth-apps/
    "github": {
        "SCOPE": [
            "read:user",
            "user:email",
            "read:org",
        ],
        # "VERIFIED_EMAIL": True,
    },
    # http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
    # NOTE: must be deleted in production settings
    "orcid": {
        "BASE_DOMAIN": "sandbox.orcid.org",
        "MEMBER_API": True,
    },
}

DISCOURSE_BASE_URL = os.getenv(
    "DISCOURSE_BASE_URL", "https://staging-discourse.comses.net"
)
DISCOURSE_SSO_SECRET = read_secret("discourse_sso_secret", "unconfigured")
DISCOURSE_API_KEY = read_secret("discourse_api_key", "unconfigured")
DISCOURSE_API_USERNAME = os.getenv("DISCOURSE_API_USERNAME", "unconfigured")

YOUTUBE_API_KEY = read_secret("youtube_api_key", "unconfigured")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCF71Bt4eDubxf0wbA7fXPfg")

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
