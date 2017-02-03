from django.conf.urls import url, include
from rest_framework import routers
from . import views
from django.views.generic import TemplateView

router = routers.DefaultRouter()
router.register(r'events', views.EventViewSet)
router.register(r'jobs', views.JobViewSet)

urlpatterns = [
    url(r'^test/$', TemplateView.as_view(template_name='home/spa_page.html'), name='test'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns += router.urls
