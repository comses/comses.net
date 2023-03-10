from core.models import MemberProfile, ComsesGroups
from library.models import Codebase, CodebaseRelease, CodebaseReleaseDownload

from django.core.cache import cache
from django.db.models import Count, F


class Metrics:
    REDIS_METRICS_KEY = "all_comses_metrics"

    def get_members_by_year(self):
        """
        Sample JSON schema
        [
            {
                "year": 2020,
                "total": 220,
                "full_members": 119,
            },
            {
                "year": 2021,
                "total": 279,
                "full_members": 111
            },
            ...
        ]
        """
        total_counts = list(
            MemberProfile.objects.public()
            .values(year=F("user__date_joined__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )
        full_member_counts = (
            ComsesGroups.FULL_MEMBER.users()
            .values(year=F("date_joined__year"))
            .annotate(full_members=Count("year"))
        )
        for mc in full_member_counts:
            # FIXME: naive double loop, probably a better way to handle this
            for tc in total_counts:
                if tc["year"] == mc["year"]:
                    tc.update(mc)

        return total_counts

    def get_codebases_by_year(self):
        """
        Sample JSON schema
        {
            "programming_language_metrics":  [
                { "year": 2013, "programming_language": "python", "count": 10 },
                { "year": 2013, "programming_language": "netlogo", "count": 37 },
                { "year": 2014, "programming_language": "python", "count": 1 },
                { "year": 2014, "programming_language": "C", "count": 3 },
                ...
            ],
            "platform_metrics": [
                { "year": 2013, "platform": "netlogo", "count": 79 },
                { "year": 2013, "platform": "mesa", "count": 13 },
                ...
            ],
            ...
        }
        """
        os_metrics = list(CodebaseRelease.objects.public().values(os=F('os'), year=F(
            "first_published_at__year")).annotate(count=Count("year")).order_by("year"))
        platform_metrics = list(CodebaseRelease.objects.public().values(platform=F(
            'platform__name'), year=F("first_published_at__year")).annotate(count=Count("year")).order_by("year"))
        programming_language_metrics = list(CodebaseRelease.objects.public().values(programming_languages=F(
            'programming_languages__name'), year=F("first_published_at__year")).annotate(count=Count("year")).order_by("year"))
        review_metrics = list(CodebaseRelease.objects.values(year=F('first_published_at__year')).annotate(count=Count("review")))

        codebase_metrics = {}
        codebase_metrics.update(os_metrics=os_metrics)
        codebase_metrics.update(platform_metrics=platform_metrics)
        codebase_metrics.update(programming_language_metrics=programming_language_metrics)
        codebase_metrics.update(review_metrics=review_metrics)
        return codebase_metrics

    def get_downloads_by_year(self):
        return list(
            CodebaseReleaseDownload.objects.values(
                year=F("date_created__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )

    def cache_all(self):
        """
        Sample JSON schema
        resulting data structure could be something like:

        {
            "members_by_year": [
                {
                    "year": 2020,
                    "total": 220,
                    "full_members": 119,
                },
                {
                    "year": 2021,
                    "total": 279,
                    "full_members": 111
                },
                ...
            ],
            "codebases_by_year": [
                {
                    "year": 2020,
                    "total": 70,
                    "netlogo": 33,
                    "python": 15,
                    "julia": 3,
                    "c": 1,
                    ...
                }
            ]
        }
        """

        all_data = {}
        all_data.update(members_by_year=self.get_members_by_year())
        all_data.update(codebases_by_year=self.get_codebases_by_year())
        all_data.update(downloads_by_year=self.get_downloads_by_year())
        # FIXME: consider TTL cache timeout
        cache.set(Metrics.REDIS_METRICS_KEY, all_data)
