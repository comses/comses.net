from core.models import MemberProfile, ComsesGroups
from library.models import CodebaseRelease, CodebaseReleaseDownload

from django.core.cache import cache
from django.db.models import Count, F
import pandas as pd


class Metrics:
    REDIS_METRICS_KEY = "all_comses_metrics"
    DEFAULT_METRICS_CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 1 week
    MINIMUM_CATEGORY_COUNT = 10  # the threshold at which we group all other nominal values into an "other" category

    def get_all_data(self):
        data = cache.get(Metrics.REDIS_METRICS_KEY)
        if not data:
            return self.cache_all()
        return data

    def cache_all(self):
        """
        caches metrics data in redis
        """
        all_data = self.get_highcharts_data()
        cache.set(
            Metrics.REDIS_METRICS_KEY, all_data, Metrics.DEFAULT_METRICS_CACHE_TIMEOUT
        )
        return all_data

    def get_highcharts_data(self):
        """
        Returns all metrics data in a format suitable for Highcharts
        Sample JSON schema
        {
            total_members: {
                "title": "Total Members",
                "y_label": "# Members",
                "start_year": 2008,
                "series": [{
                    "name": "total members",
                    "data": [40, 30, 30, 40, 40],
                }]
            },
            codebases_by_os: {
                "title": "Codebases by OS",
                "y_label": "# Codebases",
                "start_year": 2008,
                "series": [
                {
                    name: "Windows",
                    data: [40, 30, 30, 40, 40, ...],
                },
                ...
                ]
            },
            codebases_by_platform : {
                "title": "Codebases by Platform",
                "y_label": "# Codebases",
                "start_year": 2008,
                "series": [
                {
                    name: "Ubuntu Mate",
                    data: [40, 30, 30, 40, 40],
                    start_year: 2008,
                }, ...
            ]},
        }
        """
        member_metrics = self.get_members_by_year_timeseries()
        codebase_metrics = self.get_codebase_metrics_timeseries()
        min_start_year = min(
            member_metrics["start_year"], codebase_metrics["start_year"]
        )

        highcharts_data = {
            "start_year": min_start_year,
            "total_members": member_metrics["total_members"],
            "full_members": member_metrics["full_members"],
            "total_codebases": codebase_metrics["total_codebases"],
            "codebases_by_os": codebase_metrics["codebases_by_os"],
            "codebases_by_platform": codebase_metrics["codebases_by_platform"],
            "codebases_by_language": codebase_metrics["codebases_by_language"],
            "reviewed_codebases": codebase_metrics["reviewed_codebases"],
            "total_downloads": codebase_metrics["total_downloads"],
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
            .annotate(total=Count("year"))
            .order_by("year")
        )
        min_start_year = min(total_counts[0]["year"], full_member_counts[0]["year"])
        member_metrics = {
            "start_year": min_start_year,
        }
        member_metrics["total_members"] = {
            "title": "Total Members",
            "y_label": "# Members",
            "start_year": min_start_year,
            "series": [
                {
                    "name": "Members",
                    "data": self.to_timeseries(total_counts, min_start_year),
                }
            ],
        }
        member_metrics["full_members"] = {
            "title": "Full Members",
            "y_label": "# Members",
            "start_year": min_start_year,
            "series": [
                {
                    "name": "Full Members",
                    "data": self.to_timeseries(full_member_counts, min_start_year),
                }
            ],
        }
        return member_metrics

    def get_codebase_metrics_timeseries(self):
        """
        codebases_by_os: {
                "title": "Codebases by OS",
                "y_label": "# Codebases",
                "start_year": 2008,
                "series": [
                {
                    name: "Windows",
                    data: [40, 30, 30, 40, 40, ...],
                },
                ...
                ]
            },
        """
        total_codebases_by_year = list(
            CodebaseRelease.objects.public()
            .values(year=F("first_published_at__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )
        reviewed_codebases_by_year = list(
            CodebaseRelease.objects.public(peer_reviewed=True)
            .values(year=F("first_published_at__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )
        codebase_downloads = list(
            CodebaseReleaseDownload.objects.values(year=F("date_created__year"))
            .annotate(total=Count("year"))
            .order_by("year")
        )
        min_start_year = total_codebases_by_year[0]["year"]
        metrics_data = {"start_year": min_start_year}
        metrics_data["total_codebases"] = {
            "title": "Total Codebases",
            "y_label": "# Models",
            "start_year": min_start_year,
            "series": [
                {
                    "name": "Codebases",
                    "data": self.to_timeseries(total_codebases_by_year, min_start_year),
                }
            ],
        }
        metrics_data["reviewed_codebases"] = {
            "title": "Peer Reviewed Codebases",
            "y_label": "# Codebases",
            "start_year": min_start_year,
            "series": [
                {
                    "name": "Peer Reviewed Codebases",
                    "data": self.to_timeseries(
                        reviewed_codebases_by_year, min_start_year
                    ),
                }
            ],
        }
        metrics_data["total_downloads"] = {
            "title": "Total Downloads",
            "y_label": "# Downloads",
            "start_year": min_start_year,
            "series": [
                {
                    "name": "Codebase Downloads",
                    "data": self.to_timeseries(codebase_downloads, min_start_year),
                }
            ],
        }
        metrics_data["codebases_by_os"] = self.get_codebase_os_timeseries(
            min_start_year
        )
        metrics_data["codebases_by_platform"] = self.get_codebase_platform_timeseries(
            min_start_year
        )
        metrics_data[
            "codebases_by_language"
        ] = self.get_codebase_programming_language_timeseries(min_start_year)
        return metrics_data

    def get_codebase_os_timeseries(self, start_year):
        """
        Generate timeseries data for each possible codebase OS option

        Platform independent, macos, linux, windows, other

        codebases_by_os: {
            "title": "Codebases by OS",
            "y_label": "# Codebases",
            "start_year": 2008,
            "series": [
            {
                name: "Windows",
                data: [40, 30, 30, 40, 40, ...],
            },
            ...
            ]
        },
        """
        os_metrics = list(
            CodebaseRelease.objects.public()
            .values(operating_systems=F("os"), year=F("first_published_at__year"))
            .annotate(count=Count("year"))
            .order_by("year")
        )

        return {
            "title": "Codebases by OS",
            "y_label": "# Codebases",
            "start_year": start_year,
            "series": self.convert_codebase_metrics_to_timeseries(
                os_metrics, start_year, "operating_systems"
            ),
        }

    def get_codebase_platform_timeseries(self, start_year):
        platform_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                platform=F("platform_tags__name"), year=F("first_published_at__year")
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        return {
            "title": "Codebases by Platform",
            "y_label": "# Codebases",
            "start_year": start_year,
            "series": self.convert_codebase_metrics_to_timeseries(
                platform_metrics, start_year, "platform"
            ),
        }

    def get_codebase_programming_language_timeseries(self, start_year):
        programming_language_metrics = list(
            CodebaseRelease.objects.public()
            .values(
                programming_language_names=F("programming_languages__name"),
                year=F("first_published_at__year"),
            )
            .annotate(count=Count("year"))
            .order_by("year")
        )
        return {
            "title": "Codebases by Language",
            "y_label": "# Codebases",
            "start_year": start_year,
            "series": self.convert_codebase_metrics_to_timeseries(
                programming_language_metrics, start_year, "programming_language_names"
            ),
        }

    def to_timeseries(self, queryset_data, start_year):
        """
        queryset_data is a list of dicts with keys 'year' and 'total'

        return a timeseries with 0s for all missing years in-between
        """
        end_year = queryset_data[-1]["year"]
        queryset_dict = {item["year"]: item["total"] for item in queryset_data}
        data = []
        for year in range(start_year, end_year + 1):
            data.append(queryset_dict[year] if year in queryset_dict else 0)
        return data

    def convert_codebase_metrics_to_timeseries(
        self, metrics, start_year, category=None
    ):
        """
        metrics are a list of dicts with the following schema:
        [
          ...
          {'operating_systems': 'macos', 'year': 2018, 'count': 18},
          {'operating_systems': 'windows', 'year': 2018, 'count': 54},
          {'operating_systems': 'linux', 'year': 2019, 'count': 8},
          {'operating_systems': 'windows', 'year': 2019, 'count': 75},
          {'operating_systems': 'platform_independent', 'year': 2019, 'count': 92},
          ...
        ]
        category is the column index to pivot on, if not set it is assumed to be the first column name

        The data may be sparse however, and we have to account for
        missing years, filling them with 0

                Year 2008  2009    2010 2011 2012 2013
        Windows        1   Nan->0   15   22   15     ..
        macOS
        """
        df = pd.DataFrame.from_records(metrics)
        df.replace([None], "None", inplace=True)
        if category is None:
            category = df.columns[0]
        if start_year < df["year"].min():
            # add an empty record for the start year
            start_year_df = pd.DataFrame(
                [["other", start_year, 0]], columns=[category, "year", "count"]
            )
            df = pd.concat([start_year_df, df])
        # set up a pivot table with year columns and row categories (e.g., os, platform, lang)
        categories_by_year = df.pivot_table(
            values="count",
            index=category,
            columns="year",
            aggfunc="first",
            fill_value=0,
        )
        full_date_range = pd.date_range(
            str(df["year"].min()), str(df["year"].max()), freq="YS"
        )
        categories_by_year = categories_by_year.reindex(
            columns=full_date_range.year, fill_value=0
        )

        # Extract rows whose max values are less than 10,
        # and integrate into an 'other' row
        included_categories_mask = (
            categories_by_year.max(axis=1) >= Metrics.MINIMUM_CATEGORY_COUNT
        )
        other_categories_mask = (
            categories_by_year.max(axis=1) < Metrics.MINIMUM_CATEGORY_COUNT
        )
        # build a new dataframe with the included categories and an 'other' row
        result_df = categories_by_year.loc[included_categories_mask]
        # this line generates a SettingWithCopyWarning
        # See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy"
        result_df.loc["other"] = categories_by_year.loc[other_categories_mask].sum(
            axis=0
        )

        # Convert result data frame into a list of hichart objects
        start_year = int(categories_by_year.columns[0])
        category_list = result_df.index.drop_duplicates().tolist()
        category_data_list = []
        for category in category_list:
            category_data_list.append(
                {
                    "name": category,
                    "data": result_df.loc[category].tolist(),
                    "start_year": start_year,
                }
            )
        return category_data_list
