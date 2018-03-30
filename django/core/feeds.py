from datetime import datetime, timedelta, timezone
from operator import attrgetter

from django.contrib.syndication.views import Feed
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.urls import reverse_lazy
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

from core.models import Event, Job
from itertools import chain

from library.models import CodebaseRelease


class RssSiteNewsFeed(Feed):
    title = 'CoMSES jobs, events and codebase releases'
    link = reverse_lazy('rss')
    description = 'New jobs, events and codebase releases (last 120 days)'
    feed_type = Rss201rev2Feed
    feed_url = '/sitenews/rss/'

    def items(self):
        start_date = datetime.now(timezone.utc) - timedelta(days=120)
        releases = CodebaseRelease.objects \
            .public() \
            .select_related('codebase') \
            .select_related('submitter__member_profile') \
            .annotate(description=F('codebase__description')).annotate(title=Concat(F('codebase__title'), Value(' '), F('version_number'))) \
            .filter(last_modified__gt=start_date)
        jobs = Job.objects \
            .public() \
            .select_related('submitter__member_profile') \
            .filter(last_modified__gt=start_date)
        events = Event.objects \
            .public() \
            .select_related('submitter__member_profile') \
            .filter(last_modified__gt=start_date)
        return sorted(chain(releases, jobs, events), key=attrgetter('date_created'), reverse=True)

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.get_full_name()

    def item_author_link(self, item):
        return item.submitter.member_profile.get_absolute_url()

    def item_pubdate(self, item):
        return item.date_created

    def item_updateddate(self, item):
        return item.last_modified

    def item_categories(self, item):
        return [item._meta.verbose_name]


class AtomSiteNewsFeed(RssSiteNewsFeed):
    feed_type = Atom1Feed
    feed_url = '/sitenews/atom/'
    link = reverse_lazy('atom')
    subtitle = RssSiteNewsFeed.description
