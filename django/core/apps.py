from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "CoMSES CoRe App"

    def ready(self):
        pass
