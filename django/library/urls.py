from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r'codebases', views.CodebaseViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/media', views.CodebaseFilesViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/releases', views.CodebaseReleaseViewSet)
router.register(views.CodebaseReleaseFilesSipViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesSipViewSet, base_name='codebaserelease-sip-files')
router.register(views.CodebaseReleaseFilesOriginalsViewSet.get_url_matcher(),
                views.CodebaseReleaseFilesOriginalsViewSet, base_name='codebaserelease-original-files')
router.register(r'codebase-release', views.CodebaseReleaseShareViewSet, base_name='codebaserelease-share')
# router.register(r'contributors', ContributorList)

urlpatterns = [
    url(r'^contributors/$', views.ContributorList.as_view()),
    # FIXME: consider /release/upload instead
    url(r'^codebases/add/$', views.CodebaseFormCreateView.as_view(), name='codebase-add'),
    url(r'^codebases/(?P<identifier>[\w\-.]+)/edit/$', views.CodebaseFormUpdateView.as_view(),
        name='codebase-edit'),
    url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/draft/$', views.CodebaseReleaseDraftView.as_view(),
        name='codebaserelease-draft'),
    url(r'^codebases/(?P<identifier>[\w\-.]+)/version/(?P<version_number>\d+)/$',
        views.CodebaseVersionRedirectView.as_view(), name='version-redirect'),
    url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/(?P<version_number>\d+\.\d+\.\d+)/edit/$',
        views.CodebaseReleaseFormUpdateView.as_view(), name='codebaserelease-edit'),
    url(r'^codebases/(?P<identifier>[\w\-.]+)/releases/add/$',
        views.CodebaseReleaseFormCreateView.as_view(),
        name='codebaserelease-add'),
    # url(r'^codebase-release/(?P<share_uuid>[\w\-.]+)/$', views.CodebaseReleaseShareViewSet.as_view(),
    #     name='codebaserelease-share'),
] + router.urls
