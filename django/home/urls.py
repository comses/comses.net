from django.conf.urls import url, include
from django.views.generic import TemplateView
from . import views
from rest_framework.routers import SimpleRouter
from wagtail_comses_net.view_helpers import create_edit_routes

router = SimpleRouter()
router.register(r'events', views.EventViewSet)
router.register(r'jobs', views.JobViewSet)
router.register(r'tags', views.TagViewSet)

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='home/index.jinja'), name='index'),
    url(r'^', include(router.urls)),
    url(r'^resources', TemplateView.as_view(template_name='home/resources.jinja'), name='community'),
    url(r'^community', TemplateView.as_view(template_name='home/community.jinja'), name='community'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]


edit_route_form_data = {'lookup_field': 'pk', 'lookup_regex': r'\d+', 'app_name': 'home'}
for url_prefix in ['jobs', 'events']:
    urlpatterns += create_edit_routes(url_prefix=url_prefix, **edit_route_form_data)
