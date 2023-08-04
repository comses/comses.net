from jinja2.ext import Extension

from django_vite.templatetags.django_vite import vite_hmr_client, vite_asset


def _vite_hmr_client():
    return vite_hmr_client()


def _vite_asset(path, **kwargs):
    return vite_asset(path, **kwargs)


class ViteExtension(Extension):
    """
    Custom extension for jinja2 to add django-vite template tags
    """

    def __init__(self, environment):
        super(ViteExtension, self).__init__(environment)
        environment.globals["vite_hmr_client"] = _vite_hmr_client
        environment.globals["vite_asset"] = _vite_asset
