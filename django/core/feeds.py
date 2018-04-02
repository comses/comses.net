from itertools import chain

from django.contrib.syndication.views import Feed
from django.conf.urls import url
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from operator import attrgetter

from core.models import Event, Job
from library.models import CodebaseRelease

import logging

logger = logging.getLogger(__name__)


class RssSiteNewsFeed(Feed):
    title = 'CoMSES jobs, events and codebase releases'
    link = 'https://www.comses.net'
    description = 'New jobs, events and codebase releases (last 120 days)'
    feed_type = Rss201rev2Feed
    feed_url = '/feeds/rss/'

    def items(self):
        releases = CodebaseRelease.objects.latest_for_feed()
        jobs = Job.objects.latest_for_feed()
        events = Event.objects.latest_for_feed()
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
    feed_url = '/feeds/atom/'
    subtitle = RssSiteNewsFeed.description


def urlpatterns():
    return [
        url(r'^feeds/rss/$', RssSiteNewsFeed(), name='rss'),
        url(r'^feeds/atom/$', AtomSiteNewsFeed(), name='atom'),
    ]
