import logging
import re
from itertools import chain
from operator import attrgetter

from django.conf.urls import url
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

from library.models import CodebaseRelease
from .models import Event, Job

logger = logging.getLogger(__name__)

# Match invalid xml characters such as form feed
# https://lethain.com/stripping-illegal-characters-from-xml-in-python/
XML_CONTROL_CHARACTERS = re.compile('[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]')


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
        return re.sub(XML_CONTROL_CHARACTERS, '', item.title)

    def item_description(self, item):
        return re.sub(XML_CONTROL_CHARACTERS, '', str(item.description))

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
