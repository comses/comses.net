import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


def configure_sentry(*, dsn, release, environment, traces_sample_rate):
    """Initialize Sentry after environment-specific settings are finalized."""
    if not dsn:
        return
    if not 0.0 <= traces_sample_rate <= 1.0:
        raise ValueError("Sentry traces sample rate must be between 0.0 and 1.0")

    sentry_sdk.init(
        dsn=dsn,
        release=release,
        environment=environment,
        integrations=[DjangoIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=True,
    )
