from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'tagcleanup/process/$', views.process_pending_tag_cleanups, name='process_tagcleanups'),
]