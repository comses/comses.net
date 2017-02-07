from django.conf.urls import url, include
from rest_framework import routers
from . import views
from wagtail.contrib.wagtailapi import urls as wagtailapi_urls

router = routers.DefaultRouter()
router.register(r'events', views.EventViewSet)
router.register(r'jobs', views.JobViewSet)
router.register(r'tag', views.TagViewSet)

urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^', include(wagtailapi_urls)),
]

urlpatterns += router.urls
