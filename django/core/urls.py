from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework_swagger.views import get_swagger_view

from wagtail.wagtailadmin import urls as wagtailadmin_urls
from wagtail.wagtailcore import urls as wagtail_urls

from home import urls as home_urls
from library import urls as library_urls
from search import views as search_views

# from django_jinja import views as jinja_views

schema_view = get_swagger_view(title='CoMSES.net API')


"""
Primary URLConf entry point into the comses.net website
"""

urlpatterns = [
    # also pulls in urls from
    # https://github.com/ubernostrum/django-registration/blob/master/registration/auth_urls.py
    url(r'^auth/', include('registration.backends.hmac.urls')),
    # FIXME: have to hardcode this one because it gets reversed in
    url(r'^', include(home_urls, namespace='home')),
    url(r'^', include(library_urls, namespace='library')),
    url(r'^auth/', include('social_django.urls', namespace='socialauth')),
    url(r'^wagtail/admin/', include(wagtailadmin_urls)),
    url(r'^django/admin/', include(admin.site.urls)),
    url(r'^', include(wagtail_urls)),
    url(r'^api/schema/$', schema_view),
    url(r'^api/token/', obtain_jwt_token),
    url(r'^api/search/$', search_views.search, name='search'),
    url(r'^api-auth/', include('rest_framework.urls')),
]


"""
handler400 = jinja_views.BadRequest.as_view()
handler403 = jinja_views.PermissionDenied.as_view()
handler404 = jinja_views.PageNotFound.as_view()
handler500 = jinja_views.ServerError.as_view()
"""

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
