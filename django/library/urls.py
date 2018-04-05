from django.conf import settings
from django.urls import path, re_path
from rest_framework.routers import SimpleRouter

from core.settings.defaults import Environment
from . import views

app_name = 'library'

router = SimpleRouter()
router.register(r'codebases', views.CodebaseViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/media', views.CodebaseFilesViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/releases', views.CodebaseReleaseViewSet)
router.register(views.CodebaseReleaseFilesSipViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesSipViewSet, base_name='codebaserelease-sip-files')
router.register(views.CodebaseReleaseFilesOriginalsViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesOriginalsViewSet, base_name='codebaserelease-original-files')
router.register(r'codebase-release', views.CodebaseReleaseShareViewSet, base_name='codebaserelease-share')

if settings.DEPLOY_ENVIRONMENT == Environment.DEVELOPMENT:
    router.register(r'test_codebases', views.DevelopmentCodebaseDeleteView, base_name='test_codebases')

urlpatterns = [
    path('contributors/', views.ContributorList.as_view()),
    # FIXME: consider /release/upload instead
    path('codebases/add/', views.CodebaseFormCreateView.as_view(), name='codebase-add'),
    path('codebases/<slug:identifier>/edit/', views.CodebaseFormUpdateView.as_view(),
         name='codebase-edit'),
    path('codebases/<slug:identifier>/releases/draft/', views.CodebaseReleaseDraftView.as_view(),
         name='codebaserelease-draft'),
    path('codebases/<slug:identifier>/version/<int:version_number>/',
         views.CodebaseVersionRedirectView.as_view(), name='version-redirect'),
    re_path(r'^codebases/(?P<identifier>[\w\-.]+)/releases/(?P<version_number>\d+\.\d+\.\d+)/edit/$',
            views.CodebaseReleaseFormUpdateView.as_view(), name='codebaserelease-edit'),
    path('codebases/<slug:identifier>/releases/add/',
         views.CodebaseReleaseFormCreateView.as_view(), name='codebaserelease-add'),
] + router.urls