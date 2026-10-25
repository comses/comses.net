"""Settings shared by staging and production deployments."""

from .defaults import *

DEBUG = False
DJANGO_VITE_DEV_MODE = False

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
MAILGUN_API_KEY = read_secret("mail_api_key")
MAILGUN_SENDER_DOMAIN = os.getenv("MAILGUN_SENDER_DOMAIN", "mg.comses.net")
EMAIL_USE_TLS = True

# security settings from manage.py check --deploy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

HCAPTCHA_SITEKEY = os.getenv("HCAPTCHA_SITEKEY", "")
HCAPTCHA_SECRET = read_secret("hcaptcha_secret", "unconfigured")

WSGI_APPLICATION = "core.wsgi.application"

INSTALLED_APPS += ["anymail"]

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_API_KEY,
    "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
}

# Staging defaults. Production overrides the directives that differ.
CSP_DEFAULT_SRC = (
    "'self'",
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
CSP_FONT_SRC = (
    "'self'",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "maxcdn.bootstrapcdn.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "cdnjs.cloudflare.com",
    "maxcdn.bootstrapcdn.com",
    "fonts.googleapis.com",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
    "'unsafe-inline'",
)
CSP_IMG_SRC = ("'self'", "data:", "i.ytimg.com")
CSP_FRAME_SRC = (
    "'self'",
    "*.comses.net",
    "youtube.com",
    "www.youtube.com",
    "https://hcaptcha.com",
    "https://*.hcaptcha.com",
)
CSP_INCLUDE_NONCE_IN = ["script-src"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {
        "level": "WARNING",
        "handlers": ["comsesfile"],
    },
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)-7s %(name)s:%(funcName)s:%(lineno)d %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "djangofile": {
            "level": "WARNING",
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIRECTORY, "django.log"),
        },
        "comsesfile": {
            "level": "WARNING",
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIRECTORY, "comsesnet.log"),
        },
    },
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["djangofile", "console"],
            "propagate": False,
        },
        "django": {
            "level": "WARNING",
            "handlers": ["console", "djangofile"],
            "propagate": False,
        },
        "home": {
            "level": "WARNING",
            "handlers": ["comsesfile"],
            "propagate": False,
        },
        "library": {
            "level": "WARNING",
            "handlers": ["comsesfile"],
            "propagate": False,
        },
        "core": {
            "level": "WARNING",
            "handlers": ["comsesfile"],
            "propagate": False,
        },
        "huey": {
            "level": "WARNING",
            "handlers": ["comsesfile"],
            "propagate": False,
        },
    },
}

configure_request_logging(LOGGING, Path(LOG_DIRECTORY))
