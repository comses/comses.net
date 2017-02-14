from django.conf.urls import url, include
from rest_framework import routers
from . import views
from wagtail_comses_net.view_helpers import remove_api_root

code_router = routers.DefaultRouter()
code_router.register(r'code', views.CodeViewSet)

codebase_router = routers.DefaultRouter()
codebase_router.register(r'codebase', views.CodebaseReleaseViewSet)

urlpatterns = [
    url(r'^code/(?P<code_uuid>\d+)/', include(remove_api_root(codebase_router.urls)))
]

urlpatterns += remove_api_root(code_router.urls)
