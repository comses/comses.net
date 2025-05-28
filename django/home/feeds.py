from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import path
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from django.views import View
from itertools import chain
from operator import attrgetter

from library.models import Codebase, CodebaseRelease
from core.discourse import build_discourse_url, get_latest_posts
from core.models import Event, Job

import logging
import re
import requests
import sys


DEFAULT_HOMEPAGE_FEED_MAX_ITEMS = settings.DEFAULT_HOMEPAGE_FEED_MAX_ITEMS
DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour cache timeout

logger = logging.getLogger(__name__)


"""
FIXME: should probably be moved to home to prevent potential circular imports with core importing from library
"""

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
        jobs = Job.objects.live()
        events = Event.objects.live()
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


"""
Support classes for generic content feeds currently included in the landing page.
"""


@dataclass
class FeedItem:
    title: str
    link: str
    summary: str = ""
    author: str = ""
    # a relevant date for the item (date published, event start date, etc.)
    date: datetime = None
    featured_image: str = ""
    thumbnail: str = ""


class AbstractFeed(ABC):
    max_number_of_items = DEFAULT_HOMEPAGE_FEED_MAX_ITEMS
    _cache_key = None  # subclasses can define a custom cache key if needed
    cache_timeout = DEFAULT_CACHE_TIMEOUT

    def get_feed_data(self):
        return {
            "items": self.get_feed_items(),
            "last_updated": datetime.now().isoformat(),
        }

    def items(self):
        return self.get_feed_items()

    @abstractmethod
    def _get_feed_source_data(self):
        """Fetch raw data from the source and return it as a list of Python objects."""
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def to_feed_item(self, item) -> FeedItem:
        """Convert raw source data into a FeedItem."""
        raise NotImplementedError("Subclasses must implement this method.")

    @property
    def cache_key(self):
        if self._cache_key is None:
            logger.warning("using default cache key for %s", self.__class__.__name__)
            self._cache_key = f"cache_{self.__class__.__name__}"
        return self._cache_key

    def get_feed_items(self):
        source_feed_data = cache.get(self.cache_key)
        # check for cached data first
        if not source_feed_data:
            source_feed_data = self._get_feed_source_data()
            if not source_feed_data:
                # feed source may be down, do not cache
                logger.warning("No feed data found [%s]", self.cache_key)
                return []
            cache.set(self.cache_key, source_feed_data, self.cache_timeout)

        return [asdict(self.to_feed_item(item)) for item in source_feed_data]


class CodebaseFeed(AbstractFeed):
    def _get_feed_source_data(self):
        return Codebase.objects.latest_for_feed(self.max_number_of_items)

    def to_feed_item(self, codebase):
        release = codebase.latest_version
        feed_item = FeedItem(
            title=codebase.title,
            summary=release.release_notes.raw
            or codebase.summary
            or codebase.description.raw,
            link=release.get_absolute_url(),
            author=release.submitter.get_full_name(),
            date=release.date_created,
        )
        featured_image = codebase.get_featured_image()
        if featured_image:
            feed_item.featured_image = featured_image.get_rendition("width-480").url
        return feed_item


class EventFeed(AbstractFeed):
    def _get_feed_source_data(self):
        return Event.objects.latest_for_feed(self.max_number_of_items)

    def to_feed_item(self, event):
        return FeedItem(
            title=event.title,
            summary=event.summary,
            link=event.get_absolute_url(),
            author=event.submitter.get_full_name(),
            date=event.start_date,
        )


class ForumFeed(AbstractFeed):
    mock = False  # set to True for testing with mock data

    def __init__(self, mock=False):
        self.mock = mock
        super().__init__()

    def _get_feed_source_data(self):
        if self.mock:
            logger.info("Using mock data for forum feed")
        return get_latest_posts(self.max_number_of_items, mock=self.mock)

    def to_feed_item(self, post):
        return FeedItem(
            title=post["topic_title"],
            summary=post["excerpt"],
            link=build_discourse_url(post["post_url"]),
            author=post["username"],
            date=post["created_at"],
        )


class JobFeed(AbstractFeed):
    def _get_feed_source_data(self):
        return Job.objects.latest_for_feed(self.max_number_of_items)

    def to_feed_item(self, job):
        return FeedItem(
            title=job.title,
            summary=job.summary,
            link=job.get_absolute_url(),
            author=job.submitter.get_full_name(),
            date=job.date_created,
        )


class YouTubeFeed(AbstractFeed):
    def _get_feed_source_data(self):
        yt_api_url = f"{settings.YOUTUBE_API_URL}/search"
        params = {
            "part": "snippet",
            "channelId": settings.YOUTUBE_CHANNEL_ID,
            "maxResults": self.max_number_of_items,
            "order": "date",
            "key": settings.YOUTUBE_API_KEY,
        }

        response = requests.get(yt_api_url, params=params)
        if response.status_code == 200:
            yt_response = response.json()["items"]
            logger.debug("YouTube API response: %s", yt_response)
            return yt_response
        return []

    def to_feed_item(self, item):
        return FeedItem(
            title=item["snippet"]["title"],
            summary=item["snippet"]["description"],
            link=f"https://youtu.be/{item['id']['videoId']}",
            author=item["snippet"]["channelTitle"],
            date=item["snippet"]["publishedAt"],
            thumbnail=item["snippet"]["thumbnails"]["medium"]["url"],
        )
        """
        return {
                "items": [
                    {
                        "title": item["snippet"]["title"],
                        "link": f"https://youtu.be/{item['id']['videoId']}",
                        "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                    }
                    for item in data["items"]
                ]
            }
        """


class BaseFeedView(View):

    feed_class = None

    def get(self, request, *args, **kwargs):
        if not self.feed_class:
            return JsonResponse({"error": "Feed class not configured"}, status=500)
        feed_data = self.feed_class().get_feed_data()
        if feed_data is None:
            return JsonResponse({"error": "Feed not available"}, status=503)
        return JsonResponse(feed_data)


class YouTubeFeedView(BaseFeedView):
    feed_class = YouTubeFeed


class ForumFeedView(BaseFeedView):
    feed_class = ForumFeed


class EventFeedView(BaseFeedView):
    feed_class = EventFeed


class JobFeedView(BaseFeedView):
    feed_class = JobFeed


class CodebaseFeedView(BaseFeedView):
    feed_class = CodebaseFeed


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
        path(
            "homepage-feeds/code/",
            CodebaseFeedView.as_view(),
            name="codebase-feed",
        ),
        path("homepage-feeds/events/", EventFeedView.as_view(), name="event-feed"),
        path("homepage-feeds/forum/", ForumFeedView.as_view(), name="forum-feed"),
        path("homepage-feeds/jobs/", JobFeedView.as_view(), name="job-feed"),
        path("homepage-feeds/yt/", YouTubeFeedView.as_view(), name="youtube-feed"),
    ]
