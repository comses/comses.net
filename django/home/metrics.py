from core.models import MemberProfile, ComsesGroups
from library.models import CodebaseRelease, CodebaseReleaseDownload

from django.core.cache import cache
from django.db.models import Count, F


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
                    startYear: 2008,
                }
            ],
            series_codebases_platform : [
                {
                    name: "Ubuntu Mate",
                    data: [40, 30, 30, 40, 40],
                    startYear: 2008,
                }, ...
            ],
            series_codebases_langs : [
                {
                    name: "Netlogo",
                    data: [40, 30, 30, 40, 40],
                    startYear: 2008,
                },
                {
                    name: "Python",
                    data: [20, 30, 30, 30, 40],
                    startYear: 2008,
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

        metrics_data = self.get_all_data()
        member_by_year = metrics_data["members_by_year"]
        codebases_by_year = metrics_data["codebases_by_year"]
        downloads_by_year = metrics_data["downloads_by_year"]

        member_metrics = self.get_members_by_year_timeseries()
        codebase_metrics = self.get_codebase_metrics_timeseries()

        series_codebases_langs = []
        series_codebases_os = []
        series_codebases_platform = []
        data_downloads_total = {"name": "total downloads", "data": [], "start_year": 0}

        # Update members data
        start_year = 100000
        end_year = 0
        year_list = []
        for item in member_by_year:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]

        year_list = [*range(start_year, end_year + 1, 1)]

        # Update downloads data
        start_year = 100000
        end_year = 0
        year_list = []
        for item in downloads_by_year:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]
        year_list = [*range(start_year, end_year + 1, 1)]
        data_downloads_total["start_year"] = start_year

        for year in year_list:
            target = next(
                (item for item in downloads_by_year if item["year"] == year), None
            )
            if target is not None:
                if "total" in target:
                    data_downloads_total["data"].append(target["total"])
            else:
                # if no data for the year is found, data = 0.
                data_downloads_total["data"].append(0)

        # Update codebases data (os, langs, platform)
        os_list = []
        plat_list = []
        lang_list = []
        other_os_list = []
        other_plat_list = []
        other_lang_list = []
        os_year_list = []
        plat_year_list = []
        lang_year_list = []

        start_year = 100000
        end_year = 0
        temp_count = []
        for item in codebases_by_year["os_metrics"]:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]

            name = item["operating_systems"]
            if (name not in os_list) and ("count" in item):
                count = item["count"]
                if count <= 10:
                    if name in other_os_list:
                        idx = other_os_list.index(name)
                        if count > temp_count[idx]:
                            # Update the best count
                            temp_count[idx] = count
                    else:
                        other_os_list.append(name)
                        temp_count.append(count)
                else:
                    if name in other_os_list:
                        # Delete the item from other list
                        idx = other_os_list.index(name)
                        other_os_list.pop(idx)
                        temp_count.pop(idx)
                    # Add to actual list
                    os_list.append(name)
        os_year_list = [*range(start_year, end_year + 1, 1)]

        start_year = 100000
        end_year = 0
        temp_count = []
        for item in codebases_by_year["platform_metrics"]:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]

            name = item["platform"]
            if (name not in plat_list) and ("count" in item):
                count = item["count"]
                if count <= 10:
                    if name in other_plat_list:
                        idx = other_plat_list.index(name)
                        if count > temp_count[idx]:
                            # Update the best count
                            temp_count[idx] = count
                    else:
                        other_plat_list.append(name)
                        temp_count.append(count)
                else:
                    if name in other_plat_list:
                        # Delete the item from other list
                        idx = other_plat_list.index(name)
                        other_plat_list.pop(idx)
                        temp_count.pop(idx)
                    # Add to actual list
                    plat_list.append(name)
        plat_year_list = [*range(start_year, end_year + 1, 1)]

        start_year = 100000
        end_year = 0
        temp_count = []
        for item in codebases_by_year["programming_language_metrics"]:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]

            name = item["programming_language_names"]
            if (name not in lang_list) and ("count" in item):
                count = item["count"]
                if count <= 10:
                    if name in other_lang_list:
                        idx = other_lang_list.index(name)
                        if count > temp_count[idx]:
                            # Update the best count
                            temp_count[idx] = count
                    else:
                        other_lang_list.append(name)
                        temp_count.append(count)
                else:
                    if name in other_lang_list:
                        # Delete the item from other list
                        idx = other_lang_list.index(name)
                        other_lang_list.pop(idx)
                        temp_count.pop(idx)
                    # Add to actual list
                    lang_list.append(name)
        lang_year_list = [*range(start_year, end_year + 1, 1)]

        # print(os_list)
        # print(other_os_list)
        # print("os list has intersection :", (set(os_list)&set(other_os_list)))
        # print(plat_list)
        # print(other_plat_list)
        # print("plat list has intersection :", (set(plat_list)&set(other_plat_list)))
        # print(lang_list)
        # print(other_lang_list)
        # print("lang list has intersection :", set(lang_list)&set(other_lang_list))

        # Create OS data
        for os in os_list:
            series_dict = {"name": os, "data": [], "start_year": os_year_list[0]}
            for year in os_year_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["os_metrics"]
                        if (item["year"] == year) and (item["operating_systems"] == os)
                    ),
                    None,
                )
                if target is not None:
                    series_dict["data"].append(target["count"])
                else:
                    series_dict["data"].append(0)
            series_codebases_os.append(series_dict)

        # Data for os with less than 5 counts
        other_data = []
        for year in os_year_list:
            year_total = 0
            for other_os in other_os_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["os_metrics"]
                        if (item["year"] == year)
                        and (item["operating_systems"] == other_os)
                    ),
                    None,
                )
                if target is not None:
                    year_total += target["count"]
            other_data.append(year_total)
        series_codebases_os.append(
            {"name": "Others", "data": other_data, "start_year": os_year_list[0]}
        )

        # Create Platform data
        for plat in plat_list:
            series_dict = {"name": plat, "data": [], "start_year": plat_year_list[0]}
            for year in plat_year_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["platform_metrics"]
                        if (item["year"] == year) and (item["platform"] == plat)
                    ),
                    None,
                )
                if target is not None:
                    series_dict["data"].append(target["count"])
                else:
                    series_dict["data"].append(0)
            series_codebases_platform.append(series_dict)

        # Data for Platform with less than 5 counts
        other_data = []
        for year in plat_year_list:
            year_total = 0
            for other_plat in other_plat_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["platform_metrics"]
                        if (item["year"] == year) and (item["platform"] == other_plat)
                    ),
                    None,
                )
                if target is not None:
                    year_total += target["count"]
            other_data.append(year_total)
        series_codebases_platform.append(
            {"name": "Others", "data": other_data, "start_year": plat_year_list[0]}
        )

        # Create language data
        for lang in lang_list:
            series_dict = {
                "name": lang,
                "data": [],
                "start_year": lang_year_list[0],
            }
            for year in lang_year_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["programming_language_metrics"]
                        if (item["year"] == year)
                        and (item["programming_language_names"] == lang)
                    ),
                    None,
                )
                if target is not None:
                    # if "count" in target:
                    series_dict["data"].append(target["count"])
                else:
                    series_dict["data"].append(0)
            series_codebases_langs.append(series_dict)

        # Data for language with less than 10 counts
        other_data = []
        for year in lang_year_list:
            year_total = 0
            for other_lang in other_lang_list:
                target = next(
                    (
                        item
                        for item in codebases_by_year["programming_language_metrics"]
                        if (item["year"] == year)
                        and (item["programming_language_names"] == other_lang)
                    ),
                    None,
                )
                if target is not None:
                    year_total += target["count"]
            other_data.append(year_total)
        series_codebases_langs.append(
            {"name": "Others", "data": other_data, "start_year": lang_year_list[0]}
        )

        # Create data for reviewed metrics
        filtered_review_metrics = list(
            filter(
                lambda item: item["year"] != None, codebases_by_year["review_metrics"]
            )
        )
        filtered_review_metrics.sort(key=lambda item: item["year"])
        start_year = 100000
        end_year = 0
        year_list = []
        for item in filtered_review_metrics:
            if item["year"] < start_year:
                start_year = item["year"]
            if item["year"] > end_year:
                end_year = item["year"]
        year_list = [*range(start_year, end_year + 1, 1)]

        for year in year_list:
            target = next(
                (item for item in filtered_review_metrics if item["year"] == year), None
            )

        reformed_data = {
            "data_members_total": member_metrics["data_members_total"],
            "data_members_full": member_metrics["data_members_full"],
            "data_codebases_total": codebase_metrics["data_codebases_total"],
            "series_codebases_os": series_codebases_os,
            "series_codebases_platform": series_codebases_platform,
            "series_codebases_langs": series_codebases_langs,
            "data_codebases_reviewed": codebase_metrics["data_codebases_reviewed"],
            "data_downloads_total": data_downloads_total,
        }
        # print(json.dumps(reformed_data, indent = 3))
        return reformed_data

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
        data_downloads_total = {
            "name": "total downloads",
            "data": [40, 30, 30, 40, 40],
            "start_year": 0
        }
        """
        total_codebases_by_year = list(
            CodebaseRelease.objects.public()
            .values(year=F("first_published_at__year"))
            .annotate(count=Count("year"))
        )
        reviewed_codebases_by_year = list(
            CodebaseRelease.objects.public(peer_reviewed=True)
            .values(year=F("first_published_at__year"))
            .annotate(count=Count("year"))
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
        # FIXME: include series for each platform, language, and os
        return metrics_data

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
