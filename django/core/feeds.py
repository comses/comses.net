import logging
import re
from itertools import chain
from operator import attrgetter

from django.contrib.syndication.views import Feed
from django.urls import path
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

from library.models import CodebaseRelease
from .models import Event, Job

logger = logging.getLogger(__name__)

# Match invalid xml characters such as form feed
# https://lethain.com/stripping-illegal-characters-from-xml-in-python/
XML_CONTROL_CHARACTERS = re.compile('[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]')

SINGLE_FEED_MAX_ITEMS = 30


class ComsesFeed(Feed):
    feed_type = Rss201rev2Feed

    def item_title(self, item):
        return re.sub(XML_CONTROL_CHARACTERS, '', item.title)

    def item_description(self, item):
        return re.sub(XML_CONTROL_CHARACTERS, '', str(item.description))

    def item_link(self, item):
        return item.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.member_profile.name

    def item_author_link(self, item):
        return item.submitter.member_profile.get_absolute_url()

    def item_pubdate(self, item):
        return item.date_created

    def item_updateddate(self, item):
        return item.last_modified

    def item_categories(self, item):
        return [item._meta.verbose_name]


class AllFeed(ComsesFeed):
    title = 'All CoMSES jobs, events, and codebase releases'
    link = 'https://www.comses.net'
    description = 'All jobs, events, and codebase releases for initial consumption by Discourse'
    feed_url = '/feeds/all/'

    def items(self):
        releases = CodebaseRelease.objects.latest_for_feed(include_all=True)
        jobs = Job.objects.all()
        events = Event.objects.all()
        return sorted(chain(releases, jobs, events), key=attrgetter('date_created'), reverse=True)

    def item_author_name(self, item):
        return item.submitter.username


class RssSiteNewsFeed(ComsesFeed):
    title = 'CoMSES jobs, events and codebase releases'
    link = 'https://www.comses.net/'
    description = 'New jobs, events and codebase releases (last 120 days)'
    feed_url = '/feeds/rss/'

    def items(self):
        releases = CodebaseRelease.objects.latest_for_feed()
        jobs = Job.objects.latest_for_feed()
        events = Event.objects.latest_for_feed()
        return sorted(chain(releases, jobs, events), key=attrgetter('date_created'), reverse=True)


class AtomSiteNewsFeed(RssSiteNewsFeed):
    feed_type = Atom1Feed
    feed_url = '/feeds/atom/'
    subtitle = RssSiteNewsFeed.description


class RssEventFeed(ComsesFeed):
    title = 'CoMSES Net events feed'
    link = 'https://www.comses.net/events/'
    description = 'New events posted on comses.net'
    feed_url = '/feeds/events/rss/'

    def items(self):
        # FIXME: lift magic constants or make it configurable
        return Event.objects.latest_for_feed(SINGLE_FEED_MAX_ITEMS)

class AtomEventFeed(RssEventFeed):
    feed_type = Atom1Feed
    subtitle = RssEventFeed.description
    feed_url = '/feeds/events/atom/'


class RssJobFeed(ComsesFeed):
    title = 'CoMSES Net job feed'
    link = 'https://www.comses.net/jobs/'
    description = 'New jobs posted on comses.net'

    def items(self):
        return Job.objects.latest_for_feed(SINGLE_FEED_MAX_ITEMS)


class AtomJobFeed(RssJobFeed):
    feed_type = Atom1Feed
    subtitle = RssJobFeed.description


def urlpatterns():
    return [
        path('feeds/rss/', RssSiteNewsFeed(), name='rss'),
        path('feeds/atom/', AtomSiteNewsFeed(), name='atom'),
        path('feeds/events/rss/', RssEventFeed(), name='rss-events'),
        path('feeds/events/atom/', AtomEventFeed(), name='atom-events'),
        path('feeds/jobs/rss/', RssJobFeed(), name='rss-jobs'),
        path('feeds/jobs/atom/', AtomJobFeed(), name='atom-jobs'),
        path('feeds/all/', AllFeed(), name='all'),
    ]
