from django.conf.urls import url, include
from rest_framework import routers
from . import views
from wagtail.contrib.wagtailapi import urls as wagtailapi_urls
from wagtail_comses_net.view_helpers import create_edit_routes, remove_api_root

router = routers.DefaultRouter()
router.register(r'events', views.EventViewSet)
router.register(r'jobs', views.JobViewSet)
router.register(r'tags', views.TagViewSet)

urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^', include(wagtailapi_urls)),
]

urlpatterns += remove_api_root(router.urls)

edit_route_form_data = { 'lookup_field': 'pk', 'lookup_regex': r'\d+', 'app_name': 'home'}
for url_prefix in ['jobs', 'events']:
    urlpatterns += create_edit_routes(url_prefix=url_prefix, **edit_route_form_data)