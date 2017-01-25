from django.conf.urls import url, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'code', views.CodeViewSet)
router.register(r'code_release', views.CodebaseReleaseViewSet)

urlpatterns = router.urls
