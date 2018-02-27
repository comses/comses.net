from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'pendingtagcleanup/process/$', views.process_pending_tag_cleanups, name='process_pendingtagcleanups'),
]