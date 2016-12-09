from django.conf.urls import url, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'code', views.CodeViewSet)
urlpatterns = router.urls
