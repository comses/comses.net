import pathlib

from django.core.management.base import BaseCommand

import ast
import logging

from curator.models import PendingTagCleanup, CanonicalName

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up taggit tags"

    def add_arguments(self, parser):
        parser.add_argument('--run', '-r',
                            action='store_true',
                            default=False)
        parser.add_argument('--restore_directory',
                            help='directory to import canonical name mappings and from',
                            default=None)
        parser.add_argument('--method', '-m',
                            action='store_true',
                            default=False)
        parser.add_argument('--view',
                            action='store_true',
                            default=False,
                            help='view the staged tag cleanups')
        parser.add_argument('--dump',
                            action='store_true',
                            default=False,
                            help='dump staged tag cleanups and canonical name mappings to yaml files')
        parser.add_argument('--compact', '-c',
                            help='compact the staged tag cleanups (tag cleanup that share a new name are merged)')

    def handle_file(self, restore_directory):
        with restore_directory.joinpath('tag_cleanups.yml') as f:
            rows = ast.literal_eval(f.read())
        tags_cleanups = []
        for row in rows:
            tags_cleanups.append(PendingTagCleanup(new_names=row[0], old_names=row[1]))
        return tags_cleanups

    def handle_method(self):
        return PendingTagCleanup.find_groups_by_porter_stemmer(save=True)

    def handle_run(self):
        PendingTagCleanup.group_all()

    def handle_view(self):
        if PendingTagCleanup.objects.count() > 0:
            print('Tag Cleanups\n--------------------\n')
            for tag_cleanup in PendingTagCleanup.objects.iterator():
                print(tag_cleanup)
        else:
            print('No Pending Tag Cleanups!')

    def handle(self, *args, **options):
        run = options['run']
        restore_directory = pathlib.Path(options['restore_directory'] ) if options['restore_directory'] else None
        method = options['method']
        view = options['view']
        dump = options['dump']
        if run:
            self.handle_run()
        elif restore_directory is not None:
            self.handle_file(restore_directory)
        elif method:
            self.handle_method()
        elif dump:
            print('Dumping tag curation data...')
            # PendingTagCleanup.dumps('tag_cleaups.yml')
            # CanonicalName.dumps('canonical_name_mapping.csv')
        elif not view:
            raise Exception('restore directory, dump, method or view action must be specified')
        if view:
            self.handle_view()
