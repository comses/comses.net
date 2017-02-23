from django.conf.urls import url, include
from django.views.generic.base import TemplateView
from .views import CodebaseViewSet, CodebaseReleaseViewSet
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'codebase', CodebaseViewSet)
router.register(r'codebase/<uuid>/release', CodebaseReleaseViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^codebase/add', TemplateView.as_view(template_name='library/codebase/add.jinja'), name='codebase-add'),
]
