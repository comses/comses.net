from django.conf.urls import url, include
from django.views.generic.base import TemplateView
from .views import CodebaseViewSet, CodebaseReleaseViewSet
from .models import Codebase
from rest_framework.routers import SimpleRouter
from core.view_helpers import create_edit_routes

router = SimpleRouter()
router.register(r'codebases', CodebaseViewSet)
router.register(r'codebases/(?P<pk>[0-9]+)/releases', CodebaseReleaseViewSet)

urlpatterns = []
urlpatterns += create_edit_routes(prefix=Codebase._meta.object_name.lower() + 's', model=Codebase, lookup_field='pk',
                                  lookup_regex=r'\d+')

urlpatterns += [
    url(r'^', include(router.urls)),
]
