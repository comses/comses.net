from django.apps import AppConfig


class HomeAppConfig(AppConfig):
    name = 'home'

    def ready(self):
        from . import signals
