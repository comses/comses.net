from django.conf import settings
from django.core.cache import cache
from django.urls import path
from django.http import JsonResponse
import requests

from library.models import CodebaseRelease
from .models import Event, Job

FEED_MAX_ITEMS = settings.DEFAULT_HOMEPAGE_FEED_MAX_ITEMS


class HomepageFeed:
    def __call__(self, request, *args, **kwargs):
        feed = self.get_feed()
        if feed is None:
            return JsonResponse({"error": "Feed not available"}, status=503)
        return JsonResponse(feed)

    @staticmethod
    def get_feed():
        pass


class CodebaseFeed(HomepageFeed):
    @staticmethod
    def get_feed():
        releases = CodebaseRelease.objects.latest_for_feed(FEED_MAX_ITEMS)
        return {
            "items": [
                {
                    "title": release.codebase.title,
                    "summary": release.summary,
                    "link": release.get_absolute_url(),
                    "featuredImage": release.codebase.get_featured_image()
                    .get_rendition("width-480")
                    .url,
                }
                for release in releases
            ]
        }


class EventFeed(HomepageFeed):
    @staticmethod
    def get_feed():
        events = Event.objects.latest_for_feed(FEED_MAX_ITEMS)
        return {
            "items": [
                {
                    "title": event.title,
                    "summary": event.summary,
                    "author": event.submitter.get_full_name(),
                    "link": event.get_absolute_url(),
                    "date": event.start_date,
                }
                for event in events
            ]
        }


class ForumFeed(HomepageFeed):
    @staticmethod
    def get_feed():
        data = cache.get("homepage_forum_feed")

        if data is None:
            url = f"{settings.DISCOURSE_BASE_URL}/posts.json"

            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()["latest_posts"][:5]
                cache.set("homepage_forum_feed", data, 3600)

        if data is not None:
            return {
                "items": [
                    {
                        "title": post["topic_title"],
                        "author": post["username"],
                        "link": f"{settings.DISCOURSE_BASE_URL}{post["post_url"]}",
                        "date": post["created_at"],
                    }
                    for post in data
                ]
            }
        return None

class JobFeed(HomepageFeed):
    @staticmethod
    def get_feed():
        jobs = Job.objects.latest_for_feed(FEED_MAX_ITEMS)
        return {
            "items": [
                {
                    "title": job.title,
                    "summary": job.summary,
                    "author": job.submitter.get_full_name(),
                    "link": job.get_absolute_url(),
                    "date": job.date_created,
                }
                for job in jobs
            ]
        }


class YouTubeFeed(HomepageFeed):
    @staticmethod
    def get_feed():
        data = cache.get("homepage_youtube_feed")

        if data is None:
            url = f"{settings.YOUTUBE_API_URL}/search"
            params = {
                "part": "snippet",
                "channelId": settings.YOUTUBE_CHANNEL_ID,
                "maxResults": 6,
                "order": "date",
                "key": settings.YOUTUBE_API_KEY,
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                cache.set("homepage_youtube_feed", data, 3600)

        if data is not None:
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
        return None


def urlpatterns():
    return [
        path("homepage-feeds/code/", CodebaseFeed(), name="homepage-codebases"),
        path("homepage-feeds/events/", EventFeed(), name="homepage-events"),
        path("homepage-feeds/forum/", ForumFeed(), name="homepage-forum"),
        path("homepage-feeds/jobs/", JobFeed(), name="homepage-jobs"),
        path("homepage-feeds/yt/", YouTubeFeed(), name="homepage-youtube"),
    ]
