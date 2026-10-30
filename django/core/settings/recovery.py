"""Settings for operator-only recovery; never run the normal init process."""

import os

# Staging initializes Sentry during import, so disable it before that happens.
os.environ["SENTRY_DSN"] = ""

if os.environ.get("COMSES_PROVISION_ENVIRONMENT", "staging") == "prod":
    from core.settings.production import *  # noqa: F403
else:
    from core.settings.staging import *  # noqa: F403

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Clearing settings does not disable provider credentials restored in SocialApp.
EXTERNAL_AUTH_ENABLED = False
ANYMAIL = {}
SENTRY_DSN = ""
DATACITE_DRY_RUN = "true"
DATACITE_TEST_MODE = True
DATACITE_API_USERNAME = ""
DATACITE_API_PASSWORD = ""
DISCOURSE_BASE_URL = ""
DISCOURSE_API_KEY = ""
DISCOURSE_SSO_SECRET = ""
LIBRARIAN_BASE_URL = ""
LIBRARIAN_SSO_SECRET = ""
GITHUB_INTEGRATION_APP_ID = ""
GITHUB_INTEGRATION_APP_INSTALLATION_ID = 0
GITHUB_INTEGRATION_APP_PRIVATE_KEY = ""
GITHUB_INTEGRATION_APP_WEBHOOK_SECRET = ""
GITHUB_CLIENT_ID = GITHUB_CLIENT_SECRET = ""
ORCID_CLIENT_ID = ORCID_CLIENT_SECRET = ""
HCAPTCHA_SITEKEY = HCAPTCHA_SECRET = ""
YOUTUBE_API_KEY = ""
YOUTUBE_CHANNEL_ID = ""

# A consumer must remain stopped; immediate mode would execute queued work inline.
HUEY = {**HUEY, "immediate": False}  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
BASE_URL = WAGTAILADMIN_BASE_URL = "http://localhost:8080"
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_PRELOAD = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
