import csv
import logging
import os
from datetime import date

import pytz
from dateutil.parser import parse as parse_date
from django.core.management.base import BaseCommand
from django.db.models import Count, Max

from library.models import CodebaseReleaseDownload, CodebaseRelease, Codebase, PeerReview

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export download statistics CSV for a given time period"

    def add_arguments(self, parser):
        parser.add_argument('--from', help='isoformat start date (yyyy-mm-dd) e.g., --from 2018-03-15')
        parser.add_argument('--to', help='isoformat end date (yyyy-mm-dd) e.g., --to 2018-06-01. Blank defaults to today.', default=None)
        parser.add_argument('--directory', '-d', help='directory to store statistics in', default='/shared/statistics')
        parser.add_argument('--aggregations', '-a', default='release,codebase,ip,new,reviewed',
                            help='comma separated list of things to aggregate, default is release, codebase, ip, new, reviewed')

    def export_release_download_statistics(self, downloads, dest):
        releases = CodebaseRelease.objects.filter(id__in=downloads.values_list('release_id', flat=True)) \
            .prefetch_related('codebase').only('version_number', 'codebase__identifier').in_bulk()
        results = downloads.values('release_id').annotate(count=Count('*')).order_by('-count')
        with open(dest, 'w', newline='') as f:
            fieldnames = ['url', 'count', 'authors']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                release = releases[result.get('release_id')]
                authors = ', '.join([c.contributor.get_full_name() for c in release.index_ordered_release_contributors])
                writer.writerow({'url': release.get_absolute_url(), 'count': result['count'], 'authors': authors})

    def export_codebase_download_statistics(self, downloads, dest):
        codebases = Codebase.objects.filter(releases__id__in=downloads.values_list('release_id', flat=True)) \
            .prefetch_related('releases').only('identifier', 'title').in_bulk()
        results = downloads.values('release__codebase__id').annotate(count=Count('*')).order_by('-count')
        with open(dest, 'w', newline='') as f:
            fieldnames = ['url', 'count', 'title']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                codebase = codebases[result['release__codebase__id']]
                writer.writerow({'url': codebase.get_absolute_url(),
                                 'count': result['count'],
                                 'title': codebase.title})

    def export_ip_download_statistics(self, downloads, dest):
        results = downloads.values('ip_address').annotate(count=Count('*')).order_by('-count')
        with open(dest, 'w', newline='') as f:
            fieldnames = ['ip_address', 'count']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                writer.writerow(result)

    def export_reviewed_codebases(self, directory, start_date=None, end_date=None, filename='reviewed-releases.csv'):
        reviewed_releases = PeerReview.objects.completed_releases(last_modified__range=(start_date, end_date))
        header = ['url', 'title', 'published date', 'last modified', 'doi']
        with open(os.path.join(directory, filename), 'w') as out:
            writer = csv.DictWriter(out, fieldnames=header)
            writer.writeheader()
            for release in reviewed_releases:
                writer.writerow({
                    'url': release.get_absolute_url(),
                    'title': release.title,
                    'published date': release.first_published_at,
                    'last modified': release.last_modified,
                    'doi': release.doi
                })

    def export_new_and_updated_codebases(self, directory, start_date, end_date=None):
        new_codebases, updated_codebases, releases = Codebase.objects.updated_after(start_date=start_date, end_date=end_date)
        max_dates_bulk = {r['codebase_id']: r['date'] for r in releases.values('codebase_id').annotate(date=Max('last_modified'))}
        for qs, filename in [(new_codebases, 'new_codebases.csv'), (updated_codebases, 'updated_codebases.csv')]:
            with open(os.path.join(directory, filename), 'w', newline='') as f:
                fieldnames = ['url', 'title', 'last modified']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for codebase in qs:
                    writer.writerow({'url': codebase.get_absolute_url(),
                                     'title': codebase.title,
                                     'last modified': max_dates_bulk[codebase.id]})
        return releases

    def handle(self, *args, **options):
        """
        Examples

        ```
        # Extract codebase download aggregate information from 2017-01-01 to 2018-01-05
        ./manage.py curator_statistics --from 2017-01-01 --to 2018-01-05 -a codebase

        # Extract all download aggregate information from 2016-05-06 to present
        ./manage.py curator_statistics --from 2016-05-06
        ```
        """
        from_date_string = options.get('from')
        to_date_string = options.get('to')
        directory = options['directory']

        default_from_date = date.today().replace(month=1, day=1)
        default_to_date = date.today()
        from_date = parse_date(from_date_string).replace(tzinfo=pytz.UTC) if from_date_string else default_from_date
        to_date = parse_date(to_date_string).replace(tzinfo=pytz.UTC) if to_date_string else None
        aggregations = options['aggregations'].split(',')
        if to_date:
            filters = dict(date_created__range=[from_date, to_date])
        else:
            filters = dict(date_created__gte=from_date)
            to_date = default_to_date

        os.makedirs(directory, exist_ok=True)
        downloads = CodebaseReleaseDownload.objects.filter(
            release__in=CodebaseRelease.objects.public()).filter(
            **filters)
        if 'codebase' in aggregations:
            self.export_codebase_download_statistics(
                downloads,
                dest=os.path.join(directory, 'codebase_download_counts.csv'))
        if 'release' in aggregations:
            self.export_release_download_statistics(
                downloads,
                dest=os.path.join(directory, 'release_download_counts.csv'))
        if 'ip' in aggregations:
            self.export_ip_download_statistics(
                downloads,
                dest=os.path.join(directory, 'ip_download_counts.csv'))

        all_releases = None
        if 'new' in aggregations:
            self.export_new_and_updated_codebases(directory, start_date=from_date, end_date=to_date)

        if 'reviewed' in aggregations:
            self.export_reviewed_codebases(directory, start_date=from_date, end_date=to_date)
