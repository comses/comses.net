from .staging import *

# FIXME: probably better to have a common mixin instead of pulling all staging.py settings since this also brings in
# remove staging specific apps like fixture_magic
INSTALLED_APPS.remove("fixture_magic")

# datacite configuration
DATACITE_PREFIX = "10.25937"
DATACITE_TEST_MODE = False

DEBUG = False
DJANGO_VITE_DEV_MODE = False
DEPLOY_ENVIRONMENT = Environment.PRODUCTION
EMAIL_SUBJECT_PREFIX = config.get(
    "email", "EMAIL_SUBJECT_PREFIX", fallback="[comses.net]"
)
# See http://django-allauth.readthedocs.io/en/latest/providers.html#orcid for more context.
#
# staging settings include a customized sandbox orcid provider that we remove in production. In production, the ORCID
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
    "www.google-analytics.com",
    "https://comses.net",
    "https://*.comses.net",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_IMG_SRC = ("'self'", "data:", "i.ytimg.com", "www.google-analytics.com")
CSP_INCLUDE_NONCE_IN = ["script-src"]

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = BASE_URL = DEPLOY_ENVIRONMENT.base_url
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
