from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework_swagger.views import get_swagger_view
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls

from curator import wagtail_hooks, urls as curator_urls
from home import urls as home_urls
from library import urls as library_urls
from . import feeds, views
from .sitemaps import sitemaps

schema_view = get_swagger_view(title='CoMSES.net API')

"""
Primary URLConf entry point into the comses.net website
"""

handler403 = views.permission_denied
handler404 = views.page_not_found
handler500 = views.server_error

app_name = 'core'

urlpatterns = [
    path('search/', views.SearchView.as_view(), name='search'),
    path('accounts/', include('allauth.urls')),
    path('', include(home_urls, namespace='home')),
    path('', include(library_urls, namespace='library')),
    path('', include(curator_urls, namespace='curator')),
    path('discourse/sso', views.discourse_sso, name='discourse-sso'),
    path('django/admin/', admin.site.urls),
    # Replace the default wagtail admin home page
    path('wagtail/admin/', view=wagtail_hooks.DashboardView.as_view(), name='wagtailadmin_home'),
    path('wagtail/admin/', include(wagtailadmin_urls)),
    path('api/schema/', schema_view),
    path('api/token/', obtain_jwt_token),
    path('api-auth/', include('rest_framework.urls')),
    # configure sitemaps and robots.txt, see https://django-robots.readthedocs.io/en/latest/
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', include('robots.urls')),
]

urlpatterns += feeds.urlpatterns()

if settings.DEPLOY_ENVIRONMENT.is_development():
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('argh/', handler500, name='error'),
        path('make-error/', views.make_error),
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# NB: wagtail_urls are the catchall, must be last
urlpatterns.append(path('', include(wagtail_urls)))
