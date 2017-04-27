from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class HomeAppConfig(AppConfig):
    name = 'home'

    def ready(self):
        """
        Be careful not to optimize away this import it's needed to register the handlers in 
        home.signals
        :return: 
        """
        from . import signals
        logger.warning("fully loaded home signals: %s", signals)
