from unittest.mock import patch

from django.test import SimpleTestCase

from core.sentry import configure_sentry


class ConfigureSentryTestCase(SimpleTestCase):
    @patch("core.sentry.sentry_sdk.init")
    def test_configures_environment_and_trace_sampling(self, sentry_init):
        configure_sentry(
            dsn="https://public@example.invalid/1",
            release="v1.2.3",
            environment="production",
            traces_sample_rate=0.1,
        )

        sentry_init.assert_called_once()
        self.assertEqual(sentry_init.call_args.kwargs["environment"], "production")
        self.assertEqual(sentry_init.call_args.kwargs["traces_sample_rate"], 0.1)

    @patch("core.sentry.sentry_sdk.init")
    def test_empty_dsn_disables_sentry(self, sentry_init):
        configure_sentry(
            dsn="",
            release="v1.2.3",
            environment="recovery",
            traces_sample_rate=1.0,
        )

        sentry_init.assert_not_called()

    def test_rejects_invalid_trace_sampling_rate(self):
        with self.assertRaisesMessage(ValueError, "between 0.0 and 1.0"):
            configure_sentry(
                dsn="https://public@example.invalid/1",
                release="v1.2.3",
                environment="production",
                traces_sample_rate=1.1,
            )
