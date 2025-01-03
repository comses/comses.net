from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class LibraryConfig(AppConfig):
    name = "library"

    def ready(self):
        from . import signals

        logger.debug("fully loaded signals: %s for app: %s", signals, self.name)
