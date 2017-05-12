from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        """
        Be careful not to optimize away this import it's needed to register the handlers in 
        home.signals
        :return: 
        """
        from . import signals
        logger.debug("fully loaded signals: %s", signals)
