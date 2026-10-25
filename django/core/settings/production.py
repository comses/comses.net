from core.sentry import configure_sentry

from .deployed import *

# datacite configuration
DATACITE_PREFIX = "10.25937"
DATACITE_TEST_MODE = False

DEBUG = False
DJANGO_VITE_DEV_MODE = False
DEPLOY_ENVIRONMENT, WAGTAILADMIN_BASE_URL, BASE_URL = set_environment(
    Environment.PRODUCTION
)

EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[comses.net]")
# See http://django-allauth.readthedocs.io/en/latest/providers.html#orcid for more context.
#
# Default settings include a customized sandbox ORCID provider that we remove in production. In production, the ORCID
# provider works out of the box without any additional configuration.
#
# remove sandbox orcid provider from SOCIALACCOUNT_PROVIDERS
SOCIALACCOUNT_PROVIDERS.pop("orcid", None)

#########################################################
# Content Security Policy support provided via django-csp
#
# https://django-csp.readthedocs.io/en/latest/index.html
#
# Full CSP Spec: https://www.w3.org/TR/CSP/
CSP_DEFAULT_SRC = (
    "'self'",
    "https://comses.net",
    "https://*.comses.net",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_SCRIPT_SRC = (
    "'self'",
    "cdnjs.cloudflare.com",
    "browser.sentry-cdn.com",
    "www.googletagmanager.com",
    "https://comses.net",
    "https://*.comses.net",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_CONNECT_SRC = (
    "'self'",
    "ws:",  # websockets
    "api.ror.org",  # RoR affiliations dropdown support
    "cdn.jsdelivr.net",  # codemirror spell checker
    "*.comses.net",  # sentry.comses.net / forum.comses.net
    "www.google-analytics.com",  # google analytics
    "analytics.google.com",
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    "i.ytimg.com",
    "https://*.google-analytics.com",
    "https://*.googletagmanager.com",
    "https://*.analytics.google.com",
    "https://*.g.doubleclick.net",
    "https://*.google.com",
)
CSP_INCLUDE_NONCE_IN = ["script-src"]

# set up robots + sitemaps inclusion https://django-robots.readthedocs.io/en/latest/
ROBOTS_SITEMAP_URLS = [f"{BASE_URL}/sitemap.xml"]

ALLOWED_HOSTS = ["206.12.90.38", ".comses.net"]

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
            "auto_reload": False,
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
            ],
        },
    },
]

SENTRY_TRACES_SAMPLE_RATE = 0.1
configure_sentry(
    dsn=SENTRY_DSN,
    release=RELEASE_VERSION,
    environment=DEPLOY_ENVIRONMENT.name.lower(),
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
)
