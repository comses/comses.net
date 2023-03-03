from core.models import MemberProfile, ComsesGroups

from django.core.cache import cache
from django.db.models import Count, F


class Metrics:
    REDIS_METRICS_KEY = "all_comses_metrics"

    def get_members_by_year(self):
        """
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

    def cache_all(self):
        """
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
        # FIXME: consider TTL cache timeout
        cache.set(Metrics.REDIS_METRICS_KEY, all_data)

    def get_codebases_by_year():
        pass

    def get_downloads_by_year():
        pass
