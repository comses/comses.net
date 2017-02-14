from django_jinja import library
import jinja2
from django.template import Template
from webpack_loader.templatetags import webpack_loader as wl
import re


@library.global_function
def myecho(data):
    """
    Usage: {{ myecho('foo') }}
    """
    return data


@library.global_function
def render_bundle(bundle_name, extension=None, config='DEFAULT', attrs=''):
    return wl.render_bundle(bundle_name, extension, config, attrs)

# # http://stackoverflow.com/questions/6453652/how-to-add-the-current-query-string-to-an-url-in-a-django-template
# @register.simple_tag
# def query_transform(request, **kwargs):
#     updated = request.GET.copy()
#     for k, v in kwargs.iteritems():
#         updated[k] = v
#
#     return updated.urlencode()
