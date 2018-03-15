import csv

from django.core.management.base import BaseCommand

from dateutil.parser import parse as date_parse
import pytz
import logging

from django.db.models import Count

from library.models import CodebaseReleaseDownload, CodebaseRelease, Codebase

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up taggit tags"

    def add_arguments(self, parser):
        parser.add_argument('--from', '-f', help='isoformat from date')
        parser.add_argument('--to', '-t', help='isoformat to date', default=None)
        parser.add_argument('--dest', '-d', default=None)
        parser.add_argument('--level', '-l', default='release', help='aggregation level - either codebase or release')

    def export_release_download_statistics(self, downloads, dest):
        releases = CodebaseRelease.objects.filter(id__in=downloads.values_list('release_id', flat=True))\
            .prefetch_related('codebase').only('version_number', 'codebase__identifier').in_bulk()
        results = downloads.values('release_id').annotate(count=Count('*'))
        with open(dest, 'w', newline='') as f:
            fieldnames = ['url', 'count']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                writer.writerow({'url': releases[result['release_id']].get_absolute_url(), 'count': result['count']})

    def export_codebase_download_statistics(self, downloads, dest):
        codebases = Codebase.objects.filter(releases__id__in=downloads.values_list('release_id', flat=True))\
            .prefetch_related('releases').only('identifier', 'title').in_bulk()
        results = downloads.values('release__codebase__id').annotate(count=Count('*'))
        with open(dest, 'w', newline='') as f:
            fieldnames = ['url', 'count', 'title']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results.iterator():
                codebase = codebases[result['release__codebase__id']]
                writer.writerow({'url': codebase.get_absolute_url(),
                                 'count': result['count'],
                                 'title': codebase.title})

    def handle(self, *args, **options):
        """
        Examples

        ```
        # Extract codebase download aggregate information
        ./manage.py curator_statistics --from 2017-01-01 --level codebase

        # Extract release download aggregate information
        ./manage.py curator_statistics --from 2016-05-06 --dest release_download_statistics.csv
        ```
        """
        from_date = date_parse(options['from']).replace(tzinfo=pytz.UTC)
        to_date = date_parse(options['to']).replace(tzinfo=pytz.UTC) if options['to'] else None
        level = options['level']
        assert level in ['codebase', 'release']
        if to_date:
            filters = dict(date_created__range=[from_date, to_date])
        else:
            filters = dict(date_created__gte=from_date)
        dest = options['dest']
        dest = dest if dest else 'download_statistics.csv'

        downloads = CodebaseReleaseDownload.objects.filter(**filters)
        if level == 'codebase':
            self.export_codebase_download_statistics(downloads, dest)
        else:
            self.export_release_download_statistics(downloads, dest)
