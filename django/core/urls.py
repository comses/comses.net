from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework_swagger.views import get_swagger_view
from wagtail.wagtailadmin import urls as wagtailadmin_urls
from wagtail.wagtailcore import urls as wagtail_urls

from home import urls as home_urls
from library import urls as library_urls
from . import views
from .sitemaps import sitemaps

schema_view = get_swagger_view(title='CoMSES.net API')

"""
Primary URLConf entry point into the comses.net website
"""

urlpatterns = [
    url(r'^search/$', views.SearchView.as_view(), name='search'),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^', include(home_urls, namespace='home')),
    url(r'^', include(library_urls, namespace='library')),
    url(r'^discourse/sso$', views.discourse_sso, name='discourse-sso'),
    url(r'^wagtail/admin/', include(wagtailadmin_urls)),
    url(r'^django/admin/', include(admin.site.urls)),
    url(r'^api/schema/$', schema_view),
    url(r'^api/token/', obtain_jwt_token),
    url(r'^api-auth/', include('rest_framework.urls')),
    # configure sitemaps and robots.txt, see https://django-robots.readthedocs.io/en/latest/
    url('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    url(r'^robots\.txt', include('robots.urls')),
    # NB: wagtail_urls are the catchall, must be last
    url(r'^', include(wagtail_urls)),
]

handler403 = views.permission_denied
handler404 = views.page_not_found
handler500 = views.server_error

if settings.DEPLOY_ENVIRONMENT.is_development():
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
