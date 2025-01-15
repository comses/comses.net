from django.urls import path
from .views import autopost_view

urlpatterns = [
    path('autopost/', autopost_view, name='autopost'),
]
