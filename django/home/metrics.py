from core.models import MemberProfile, ComsesGroups
from library.models import CodebaseRelease, CodebaseReleaseDownload

from django.core.cache import cache
from django.db.models import Count, F
import pandas as pd
import numpy as np

class Metrics:
    REDIS_METRICS_KEY = "all_comses_metrics"

    def get_all_data(self):
        data = cache.get(Metrics.REDIS_METRICS_KEY)
        if not data:
            return self.cache_all()
        return data

    def get_highcharts_data(self):
        """
        Sample JSON schema
        {
            data_members_total : {
                "name": "total members",
                "data": [40, 30, 30, 40, 40],
                "start_year": 2008
            },
            data_members_full : {
                "name": "full members",
                "data": [40, 30, 30, 40, 40],
                "start_year": 2008
            },
            data_codebases_total : {
                "name": "total codebases",
                "data": [40, 30, 30, 40, 40],
                "start_year": 2008
            },
            series_codebases_os : [
                {
                    name: "Windows",
                    data: [40, 30, 30, 40, 40],
                    start_year: 2008,
                }
            ],
            series_codebases_platform : [
                {
                    name: "Ubuntu Mate",
                    data: [40, 30, 30, 40, 40],
                    start_year: 2008,
                }, ...
            ],
            series_codebases_langs : [
                {
                    name: "Netlogo",
                    data: [40, 30, 30, 40, 40],
                    start_year: 2008,
                },
                {
                    name: "Python",
                    data: [20, 30, 30, 30, 40],
                    start_year: 2008,
                }, ....
            ],
            data_codebases_reviewed : {
                "name": "reviewed codebases",
                "data": [40, 30, 30, 40, 40],
                "start_year": 0
            },
            data_downloads_total = {
                "name": "total downloads",
                "data": [40, 30, 30, 40, 40],
                "start_year": 0
            }

        }
        """
        member_metrics = self.get_members_by_year_timeseries()
        codebase_metrics = self.get_codebase_metrics_timeseries()

        highcharts_data = {
            "data_members_total": member_metrics["data_members_total"],
            "data_members_full": member_metrics["data_members_full"],
            "data_codebases_total": codebase_metrics["data_codebases_total"],
            "series_codebases_os": codebase_metrics["series_codebases_os"],
            "series_codebases_platform": codebase_metrics["series_codebases_platform"],
            "series_codebases_langs": codebase_metrics["series_codebases_langs"],
            "data_codebases_reviewed": codebase_metrics["data_codebases_reviewed"],
            "data_downloads_total": codebase_metrics["data_downloads_total"],
        }

        return highcharts_data

    def get_members_by_year_timeseries(self):
        """
        data_members_total: {
            "name": "total members",
            "data": [40, 30, 30, 40, 40],
            "start_year": 2008
        },
        data_members_full: {
            "name": "full members",
            "data": [40, 30, 30, 40, 40],
            "start_year": 2008
        }
        """
        total_counts = list(
            MemberProfile.objects.public()
            .values(year=F("user__date_joined__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )
        full_member_counts = list(
            ComsesGroups.FULL_MEMBER.users()
            .values(year=F("date_joined__year"))
            .annotate(full_members=Count("year"))
            .order_by("year")
        )
        member_metrics = {}
        member_metrics["data_members_total"] = {
            "name": "Total Members",
            "data": [item["total"] for item in total_counts],
            "start_year": total_counts[0]["year"],
        }
        member_metrics["data_members_full"] = {
            "name": "Full Members",
            "data": [item["full_members"] for item in full_member_counts],
            "start_year": full_member_counts[0]["year"],
        }
        return member_metrics

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

    def get_codebase_metrics_timeseries(self):
        """
        data_codebases_total : {
            "name": "total codebases",
            "data": [40, 30, 30, 40, 40],
            "start_year": 2008
        },
        data_codebases_reviewed : {
            "name": "reviewed codebases",
            "data": [40, 30, 30, 40, 40],
            "start_year": 0
        },
        """
        total_codebases_by_year = list(
            CodebaseRelease.objects.public()
            .values(year=F("first_published_at__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )
        reviewed_codebases_by_year = list(
            CodebaseRelease.objects.public(peer_reviewed=True)
            .values(year=F("first_published_at__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )
        codebase_downloads = list(
            CodebaseReleaseDownload.objects.values(year=F("date_created__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )

        metrics_data = {}
        metrics_data["data_codebases_total"] = {
            "name": "Total Codebases",
            "data": [item["count"] for item in total_codebases_by_year],
            "start_year": total_codebases_by_year[0]["year"],
        }
        metrics_data["data_codebases_reviewed"] = {
            "name": "Peer Reviewed Codebases",
            "data": [item["count"] for item in reviewed_codebases_by_year],
            "start_year": reviewed_codebases_by_year[0]["year"],
        }
        metrics_data["data_downloads_total"] = {
            "name": "Codebase Downloads",
            "data": [item["count"] for item in codebase_downloads],
            "start_year": codebase_downloads[0]["year"],
        }
        metrics_data["series_codebases_os"] = self.get_codebase_os_timeseries()
        metrics_data["series_codebases_platform"] = self.get_codebase_platform_timeseries()
        metrics_data["series_codebases_langs"] = self.get_codebase_programming_language_timeseries()
        return metrics_data


    def convert_codebase_metrics_to_timeseries(self, metrics, category):
        """
            The data may be sparse however, and we have to account for
            missing years filling them with 0 using fillna(0)

                    Year 2008  2009    2010 2011 2012 2013
            Windows        1   Nan->0   15   22   15     ..  
            macOS   

        """
        df = pd.DataFrame.from_records(metrics)
        df.replace([None], 'None', inplace=True)

        # Pivot table into the form whose column is year 
        # and row is category (os, platform, lang).
        tmp_df = df.pivot_table(values='count', index=category, columns='year', aggfunc='first')
        tmp_df = tmp_df.fillna(0).apply(np.int64)

        # Extract rows whose max values are less than 10, 
        # and integrate into 'others' row
        bool_mask1 = (tmp_df.max(axis=1) >= 10)
        bool_mask2 = (tmp_df.max(axis=1) < 10)
        result_df = tmp_df.loc[bool_mask1]
        result_df.loc['others'] = tmp_df.loc[bool_mask2].sum(axis=0)

        # Conver df into a list of hichart objects
        year_list = df['year'].drop_duplicates().tolist()
        category_list = result_df.index.drop_duplicates().tolist()
        category_data_list = []
        for category in category_list:
            category_data_list.append({
                "name" : category,
                "data" : result_df.loc[category].tolist(),
                "start_year": year_list[0]
            })
        return category_data_list

    def get_codebase_os_timeseries(self):
        """
        Generate timeseries data for each possible codebase OS option

        Platform independent, macos, linux, windows, other

        series_codebases_os : [
            {
                name: "Windows",
                data: [40, 30, 30, 40, 40],
                start_year: 2008,
            },
            {
                name: "Mac",
                data: [30, 10, 17, 29],
                start_year: 2008,
            }
        ],
        """
        os_metrics = list(
            CodebaseRelease.objects.public()
            .values(operating_systems=F("os"), year=F("first_published_at__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )

        os_data_list = self.convert_codebase_metrics_to_timeseries(os_metrics, 'operating_systems')
        return os_data_list
        
    def get_codebase_platform_timeseries(self):
        """
        series_codebases_platform : [
            {
                name: "Ubuntu Mate",
                data: [40, 30, 30, 40, 40],
                start_year: 2008,
            }, ...
        ],
        series_codebases_langs : [
            {
                name: "Netlogo",
                data: [40, 30, 30, 40, 40],
                start_year: 2008,
            },
            {
                name: "Python",
                data: [20, 30, 30, 30, 40],
                start_year: 2008,
            }, ....
        ],
        """
        platform_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                platform=F("platform_tags__name"), year=F("first_published_at__year")
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        platform_data_list = self.convert_codebase_metrics_to_timeseries(platform_metrics, 'platform')
        return platform_data_list

    def get_codebase_programming_language_timeseries(self):   
        programming_language_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                programming_language_names=F("programming_languages__name"),
                year=F("first_published_at__year"),
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        programming_language_data_list = self.convert_codebase_metrics_to_timeseries(programming_language_metrics, 'programming_language_names')
        return programming_language_data_list

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
        os_metrics = list(
            CodebaseRelease.objects.public()
            .values(operating_systems=F("os"), year=F("first_published_at__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )
        platform_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                platform=F("platform_tags__name"), year=F("first_published_at__year")
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        programming_language_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                programming_language_names=F("programming_languages__name"),
                year=F("first_published_at__year"),
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        review_metrics = list(
            CodebaseRelease.objects.values(year=F("first_published_at__year")).annotate(
                count=Count("review")
            )
        )

        codebase_metrics = {}
        codebase_metrics.update(os_metrics=os_metrics)
        codebase_metrics.update(platform_metrics=platform_metrics)
        codebase_metrics.update(
            programming_language_metrics=programming_language_metrics
        )
        codebase_metrics.update(review_metrics=review_metrics)
        return codebase_metrics

    def get_downloads_by_year(self):
        return list(
            CodebaseReleaseDownload.objects.values(year=F("date_created__year"))
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
        all_data.update(members_by_year=self.get_members_by_year_timeseries())
        all_data.update(codebases_by_year=self.get_codebases_by_year())
        all_data.update(downloads_by_year=self.get_downloads_by_year())
        # FIXME: consider TTL cache timeout
        cache.set(Metrics.REDIS_METRICS_KEY, all_data)
        return all_data
