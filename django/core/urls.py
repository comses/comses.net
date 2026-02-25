from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import SimpleRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.contrib.sitemaps.views import sitemap

from curator import urls as curator_urls
from home import urls as home_urls
from library import urls as library_urls
from . import views

"""
Primary URLConf entry point into the comses.net website
"""

handler403 = views.permission_denied
handler404 = views.page_not_found
handler500 = views.server_error

app_name = "core"


def get_core_urls():
    router = SimpleRouter()
    router.register(r"tags", views.TagListView, basename="tag")
    router.register(r"events", views.EventViewSet, basename="event")
    router.register(r"jobs", views.JobViewSet, basename="job")
    router.register(r"users", views.MemberProfileViewSet, basename="profile")

    return [
        path(
            "accounts/profile/",
            views.ProfileRedirectView.as_view(),
            name="account-profile",
        ),
        path(
            "users/<int:user__pk>/edit/",
            views.ProfileUpdateView.as_view(),
            name="profile-edit",
        ),
        path(
            "users/<int:user__pk>/upload_picture/",
            views.MemberProfileImageUploadView.as_view(),
            name="profile-avatar-upload",
        ),
        path("users/follow/", views.ToggleFollowUser.as_view(), name="follow-user"),
        path(
            "events/<int:pk>/delete/",
            views.EventMarkDeletedView.as_view(),
            name="event-delete",
        ),
        path(
            "events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event-edit"
        ),
        path("events/add/", views.EventCreateView.as_view(), name="event-add"),
        path(
            "jobs/<int:pk>/delete/",
            views.JobMarkDeletedView.as_view(),
            name="job-delete",
        ),
        path("jobs/<int:pk>/edit/", views.JobUpdateView.as_view(), name="job-edit"),
        path("jobs/add/", views.JobCreateView.as_view(), name="job-add"),
        path("discourse/sso", views.discourse_sso, name="discourse-sso"),
    ] + router.urls


urlpatterns = [
    path("", include(home_urls, namespace="home")),
    path("", include(library_urls, namespace="library")),
    path("", include(curator_urls, namespace="curator")),
    path("", include((get_core_urls(), "core"), namespace="core")),
    path("accounts/", include("allauth.urls")),
    path("django/admin/", admin.site.urls),
    path("wagtail/admin/", include(wagtailadmin_urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api-auth/", include("rest_framework.urls")),
    # configure sitemaps and robots.txt, see https://django-robots.readthedocs.io/en/latest/
    # https://docs.wagtail.org/en/stable/reference/contrib/sitemaps.html
    path("sitemap.xml", sitemap),
    path("robots.txt", include("robots.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEPLOY_ENVIRONMENT.is_development:
    urlpatterns += [
        path("argh/", handler500, name="error"),
        path("make-error/", views.make_error),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if not settings.TESTING:
        from debug_toolbar.toolbar import debug_toolbar_urls

        urlpatterns += debug_toolbar_urls()


# NB: wagtail_urls are the catchall, must be last
urlpatterns.append(path("", include(wagtail_urls)))
