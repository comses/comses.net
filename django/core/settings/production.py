from .staging import *

# FIXME: probably better to have a common mixin instead of pulling all staging.py settings since this also brings in
# remove staging specific apps like fixture_magic
INSTALLED_APPS.remove("fixture_magic")

DEBUG = False
DEPLOY_ENVIRONMENT = Environment.PRODUCTION
EMAIL_SUBJECT_PREFIX = config.get(
    "email", "EMAIL_SUBJECT_PREFIX", fallback="[comses.net]"
)
# http://django-allauth.readthedocs.io/en/latest/providers.html#orcid
# remove sandbox orcid provider
SOCIALACCOUNT_PROVIDERS.pop("orcid", None)

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
BASE_URL = DEPLOY_ENVIRONMENT.base_url
# set up robots + sitemaps inclusion https://django-robots.readthedocs.io/en/latest/
ROBOTS_SITEMAP_URLS = [f"{BASE_URL}/sitemap.xml"]

ALLOWED_HOSTS = ["206.12.90.38", ".comses.net"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "APP_DIRS": True,
        "OPTIONS": {
            "extensions": [
                "webpack_loader.contrib.jinja2ext.WebpackExtension",
                "wagtail.contrib.settings.jinja2tags.settings",
                "wagtail.core.jinja2tags.core",
                "wagtail.admin.jinja2tags.userbar",
                "wagtail.images.jinja2tags.images",
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
