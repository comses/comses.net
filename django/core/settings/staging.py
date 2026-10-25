from core.sentry import configure_sentry

from .deployed import *

DEPLOY_ENVIRONMENT, WAGTAILADMIN_BASE_URL, BASE_URL = set_environment(
    Environment.STAGING
)

# DataCite sandbox configuration is inherited from defaults.
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[staging.comses.net]")
ALLOWED_HOSTS = [".comses.net"]

INSTALLED_APPS += ["fixture_magic"]

SENTRY_TRACES_SAMPLE_RATE = 1.0
configure_sentry(
    dsn=SENTRY_DSN,
    release=RELEASE_VERSION,
    environment=DEPLOY_ENVIRONMENT.name.lower(),
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
)
