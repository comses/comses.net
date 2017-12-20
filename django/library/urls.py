from django.conf.urls import url

from core.routers import AddEditRouter
from . import views

router = AddEditRouter()
router.register(r'codebases', views.CodebaseViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/media', views.CodebaseFilesViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/releases', views.CodebaseReleaseViewSet)
router.register(views.CodebaseReleaseFilesSipViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesSipViewSet, base_name='codebaserelease-sip-files')
router.register(views.CodebaseReleaseFilesOriginalsViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesOriginalsViewSet, base_name='codebaserelease-original-files')
# router.register(r'contributors', ContributorList)

urlpatterns = [
      url(r'^contributors/$', views.ContributorList.as_view()),
      # FIXME: consider /release/upload instead
      url(r'^codebases/add/$', views.CodebaseFormCreateView.as_view(), name='codebase-add'),
      url(r'^codebases/(?P<identifier>[\w\-.]+)/edit/$', views.CodebaseFormUpdateView.as_view(),
          name='codebase-edit'),
      url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/draft/$', views.CodebaseReleaseDraftView.as_view(),
          name='codebaserelease-draft'),
      url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/(?P<version_number>\d+\.\d+\.\d+)/edit/$',
          views.CodebaseReleaseFormUpdateView.as_view(), name='codebaserelease-edit'),
      url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/add/$',
          views.CodebaseReleaseFormCreateView.as_view(),
          name='codebaserelease-add'),
] + router.urls
