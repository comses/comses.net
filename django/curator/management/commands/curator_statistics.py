import csv

import os
from django.core.management.base import BaseCommand

from dateutil.parser import parse as date_parse
import pytz
import logging

from django.db.models import Count, F, Max, Prefetch

from library.models import CodebaseReleaseDownload, CodebaseRelease, Codebase

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up taggit tags"

    def add_arguments(self, parser):
        parser.add_argument('--from', '-f', help='isoformat from date')
        parser.add_argument('--to', '-t', help='isoformat to date', default=None)
        parser.add_argument('--directory', '-d', help='directory to store statistics in', default='/shared/statistics')
        parser.add_argument('--aggregations', '-a', default='release,codebase,ip,new',
                            help='aggregations - comma separated list of release, codebase, ip')

    def export_release_download_statistics(self, downloads, dest):
        releases = CodebaseRelease.objects.filter(id__in=downloads.values_list('release_id', flat=True)) \
            .prefetch_related('codebase').only('version_number', 'codebase__identifier').in_bulk()
        results = downloads.values('release_id').annotate(count=Count('*')).order_by('-count')
        with open(dest, 'w', newline='') as f:
            fieldnames = ['url', 'count']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                writer.writerow({'url': releases[result['release_id']].get_absolute_url(), 'count': result['count']})

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

    def export_new_and_updated_codebases(self, filters, directory):
        in_range_releases = CodebaseRelease.objects.filter(**filters)
        if 'date_created__range' in filters:
            out_range_releases = CodebaseRelease.objects.exclude(date_created__gte=filters['date_created__range'][0])
        else:
            out_range_releases = CodebaseRelease.objects.exclude(**filters)
        new_codebases = Codebase.objects.public().filter(releases__in=in_range_releases)\
            .exclude(releases__in=out_range_releases).distinct().order_by('title')
        updated_codebases = Codebase.objects.public().filter(releases__in=in_range_releases)\
            .filter(releases__in=out_range_releases).distinct().order_by('title')

        max_dates_bulk = {r['codebase_id']: r['date'] for r in in_range_releases
            .values('codebase_id').annotate(date=Max('date_created'))}
        for qs, filename in [(new_codebases, 'new_codebases.csv'), (updated_codebases, 'updated_codebases.csv')]:
            with open(os.path.join(directory, filename), 'w', newline='') as f:
                fieldnames = ['url', 'title', 'date']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for codebase in qs.iterator():
                    writer.writerow({'url': codebase.get_absolute_url(),
                                     'title': codebase.title,
                                     'date': max_dates_bulk[codebase.id]})

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
        from_date = date_parse(options['from']).replace(tzinfo=pytz.UTC)
        to_date = date_parse(options['to']).replace(tzinfo=pytz.UTC) if options['to'] else None
        aggregations = options['aggregations'].split(',')
        if to_date:
            filters = dict(date_created__range=[from_date, to_date])
        else:
            filters = dict(date_created__gte=from_date)
        directory = options['directory']

        os.makedirs(directory, exist_ok=True)
        downloads = CodebaseReleaseDownload.objects.filter(release__in=CodebaseRelease.objects.public())\
            .filter(**filters)
        if 'codebase' in aggregations:
            self.export_codebase_download_statistics(downloads,
                                                     dest=os.path.join(directory, 'codebase_download_counts.csv'))
        if 'release' in aggregations:
            self.export_release_download_statistics(downloads,
                                                    dest=os.path.join(directory, 'release_download_counts.csv'))
        if 'ip' in aggregations:
            self.export_ip_download_statistics(downloads,
                                               dest=os.path.join(directory, 'ip_download_counts.csv'))
        if 'new' in aggregations:
            self.export_new_and_updated_codebases(filters=filters, directory=directory)
