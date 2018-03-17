from django.contrib.sitemaps import Sitemap

from .models import Event, Job


# set up sitemap ala https://docs.djangoproject.com/en/1.11/ref/contrib/sitemaps/

class BaseSitemap(Sitemap):

    changefreq = "never"

    def items(self):
        return self.model.objects.all()

    def lastmod(self, obj):
        return obj.last_modified

class EventSitemap(BaseSitemap):

    model = Event


class JobSitemap(Sitemap):

    model = Job


"""
class LibrarySitemap(Sitemap):

    models = Codebase
"""

sitemaps = {
#    'events': EventSitemap,
#    'jobs': JobSitemap,
    # 'library': LibrarySitemap,
    # 'community': CommunitySitemap,
}
