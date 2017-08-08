from django.conf.urls import url

from core.routers import AddEditRouter
from .views import CodebaseViewSet, CodebaseReleaseViewSet, ContributorList, CodebaseReleaseUploadView

router = AddEditRouter()
router.register(r'codebases', CodebaseViewSet)
router.register(r'codebases/(?P<identifier>[\w\-.]+)/releases', CodebaseReleaseViewSet)
# router.register(r'contributors', ContributorList)

urlpatterns = router.urls + [
    # url(r'^codebases/add/$', login_required(TemplateView(template_name='library/codebases/add.jinja').as_view())),
    url(r'^contributors/$', ContributorList.as_view()),
    # FIXME: consider /release/upload instead
    url(r'^codebases/(?P<identifier>\w+)/update/create_release/$', CodebaseReleaseUploadView.as_view()),
]
