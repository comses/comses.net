from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

from search import views as search_views
from wagtail.wagtailadmin import urls as wagtailadmin_urls

from home import urls as wagtailapi_urls
from library import urls as library_urls

from rest_framework_swagger.views import get_swagger_view
from rest_framework_jwt.views import obtain_jwt_token

from django.views.generic import TemplateView

schema_view = get_swagger_view(title='CoMSES.net API')

urlpatterns = [
    url(r'^wagtail/admin/', include(wagtailadmin_urls)),

    url(r'^', include(library_urls)),
    url(r'^api/search/$', search_views.search, name='search'),
    url(r'^', include(wagtailapi_urls)),
    url(r'^api/schema/$', schema_view),
    url(r'^api/token/', obtain_jwt_token),
    url(r'^$', TemplateView.as_view(template_name='base.jinja'), name='home'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
