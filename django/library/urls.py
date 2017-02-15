from django.conf.urls import url, include
from . import views
from wagtail_comses_net.view_helpers import RouterWithoutAPIRoot

code_router = RouterWithoutAPIRoot()
code_router.register(r'code', views.CodeViewSet)

codebase_router = RouterWithoutAPIRoot()
codebase_router.register(r'codebase', views.CodebaseReleaseViewSet)

urlpatterns = [
    url(r'^(?P<code_uuid>\d+)/', include(codebase_router.urls_without_api_root))
]

urlpatterns += code_router.urls_without_api_root
