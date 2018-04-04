from django.conf.urls import url

from . import views

app_name = 'curator'

urlpatterns = [
    url(r'tagcleanup/process/$', views.process_pending_tag_cleanups, name='process_tagcleanups'),
]
