from django.urls import path

import core.views
from . import views

handler403 = core.views.permission_denied
handler404 = core.views.page_not_found
handler500 = core.views.server_error

app_name = 'conference'

urlpatterns = [
    path('conference/2018/submit/', views.Submission2018View.as_view(), name='2018-submit'),
]