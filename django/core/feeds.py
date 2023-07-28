import logging
import re
import sys
from itertools import chain
from operator import attrgetter

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import path
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed

from library.models import CodebaseRelease
from .models import Event, Job

logger = logging.getLogger(__name__)


# invalid xml characters regex pulled from
# https://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
invalid_unichrs = [
    (0x00, 0x08),
    (0x0B, 0x0C),
    (0x0E, 0x1F),
    (0x7F, 0x84),
    (0x86, 0x9F),
    (0xFDD0, 0xFDDF),
    (0xFFFE, 0xFFFF),
]

if sys.maxunicode >= 0x10000:
    invalid_unichrs.extend(
        [
            (0x1FFFE, 0x1FFFF),
            (0x2FFFE, 0x2FFFF),
            (0x3FFFE, 0x3FFFF),
            (0x4FFFE, 0x4FFFF),
            (0x5FFFE, 0x5FFFF),
            (0x6FFFE, 0x6FFFF),
            (0x7FFFE, 0x7FFFF),
            (0x8FFFE, 0x8FFFF),
            (0x9FFFE, 0x9FFFF),
            (0xAFFFE, 0xAFFFF),
            (0xBFFFE, 0xBFFFF),
            (0xCFFFE, 0xCFFFF),
            (0xDFFFE, 0xDFFFF),
            (0xEFFFE, 0xEFFFF),
            (0xFFFFE, 0xFFFFF),
            (0x10FFFE, 0x10FFFF),
        ]
    )
invalid_character_ranges = [
    rf"{chr(low)}-{chr(high)}" for (low, high) in invalid_unichrs
]
XML_INVALID_CHARACTER_REGEX = re.compile(f"[{''.join(invalid_character_ranges)}]")

SINGLE_FEED_MAX_ITEMS = settings.DEFAULT_FEED_MAX_ITEMS


class ComsesFeed(Feed):
    feed_type = Rss201rev2Feed

    def item_title(self, item):
        return XML_INVALID_CHARACTER_REGEX.sub("", item.title)

    def item_description(self, item):
        return XML_INVALID_CHARACTER_REGEX.sub("", str(item.description))

    def item_link(self, item):
        return item.get_absolute_url()

    def item_author_name(self, item):
        return item.submitter.username

    def item_author_link(self, item):
        return item.submitter.member_profile.get_absolute_url()

    def item_pubdate(self, item):
        return item.date_created

    def item_updateddate(self, item):
        return item.last_modified

    def item_categories(self, item):
        return [item._meta.verbose_name]


class AllFeed(ComsesFeed):
    title = "All CoMSES jobs, events, and codebase releases"
    link = "https://www.comses.net"
    description = (
        "All jobs, events, and codebase releases for initial consumption by Discourse"
    )
    feed_url = "/feeds/all/"

    def items(self):
        releases = CodebaseRelease.objects.latest_for_feed(include_all=True)
        jobs = Job.objects.all()
        events = Event.objects.all()
        return sorted(
            chain(releases, jobs, events), key=attrgetter("date_created"), reverse=True
        )

    def item_author_name(self, item):
        return item.submitter.username


class RssSiteNewsFeed(ComsesFeed):
    title = "CoMSES jobs, events and codebase releases"
    link = "https://www.comses.net/"
    description = "New jobs, events and codebase releases (last 120 days)"
    feed_url = "/feeds/rss/"

    def items(self):
        releases = CodebaseRelease.objects.latest_for_feed()
        jobs = Job.objects.latest_for_feed()
        events = Event.objects.latest_for_feed()
        return sorted(
            chain(releases, jobs, events), key=attrgetter("date_created"), reverse=True
        )


class AtomSiteNewsFeed(RssSiteNewsFeed):
    feed_type = Atom1Feed
    feed_url = "/feeds/atom/"
    subtitle = RssSiteNewsFeed.description


class RssEventFeed(ComsesFeed):
    title = "CoMSES Net Events RSS"
    link = "https://www.comses.net/events/"
    description = "New events posted on comses.net"
    feed_url = "/feeds/events/rss/"

    def items(self):
        # FIXME: lift magic constants or make it configurable
        return Event.objects.latest_for_feed(SINGLE_FEED_MAX_ITEMS)


class AtomEventFeed(RssEventFeed):
    feed_type = Atom1Feed
    subtitle = RssEventFeed.description
    feed_url = "/feeds/events/atom/"


class RssJobFeed(ComsesFeed):
    title = "CoMSES Net Job RSS"
    link = "https://www.comses.net/jobs/"
    description = "New jobs posted on comses.net"

    def items(self):
        return Job.objects.latest_for_feed(SINGLE_FEED_MAX_ITEMS)


class RssCodebaseFeed(ComsesFeed):
    title = "CoMSES Net Computational Models Feed"
    link = "https://www.comses.net/codebases/"
    description = "New computational models posted to comses.net"
    feed_url = "/feeds/code/rss/"

    def items(self):
        return CodebaseRelease.objects.latest_for_feed(SINGLE_FEED_MAX_ITEMS)


class AtomJobFeed(RssJobFeed):
    feed_type = Atom1Feed
    subtitle = RssJobFeed.description


def urlpatterns():
    return [
        path("feeds/rss/", RssSiteNewsFeed(), name="rss"),
        path("feeds/atom/", AtomSiteNewsFeed(), name="atom"),
        path("feeds/events/rss/", RssEventFeed(), name="rss-events"),
        path("feeds/events/atom/", AtomEventFeed(), name="atom-events"),
        path("feeds/jobs/rss/", RssJobFeed(), name="rss-jobs"),
        path("feeds/jobs/atom/", AtomJobFeed(), name="atom-jobs"),
        path("feeds/code/rss/", RssCodebaseFeed(), name="rss-codebases"),
        path("feeds/all/", AllFeed(), name="all"),
    ]
