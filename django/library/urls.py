from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from core.view_helpers import create_edit_routes
from .models import Codebase
from .views import CodebaseViewSet, CodebaseReleaseViewSet, ContributorList, CodebaseReleaseUploadView

router = SimpleRouter()
router.register(r'codebases', CodebaseViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/releases', CodebaseReleaseViewSet)
# router.register(r'contributors', ContributorList)

urlpatterns = create_edit_routes(
    prefix='codebases',
    model=Codebase,
    lookup_field='identifier',
    lookup_regex=r'[\w\-.]+'
) + router.urls + [
    url(r'^contributors/$', ContributorList.as_view()),
    url(r'^codebases/(?P<identifier>\w+)/update/create_release/', CodebaseReleaseUploadView.as_view()),
]
