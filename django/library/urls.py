from django.conf.urls import url, include
from django.views.generic.base import TemplateView
from .views import CodebaseViewSet, CodebaseReleaseViewSet
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'codebases', CodebaseViewSet, base_name='codebase')
router.register(r'codebases/(?P<identifier>\w+)/releases', CodebaseReleaseViewSet, base_name='release')

urlpatterns = router.urls + [
    url(r'^codebase/add', TemplateView.as_view(template_name='library/codebase/add.jinja'), name='codebase-add'),
]
