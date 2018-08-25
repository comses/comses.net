import logging
import pathlib

from django.core.management.base import BaseCommand

from curator.models import TagCleanup, PENDING_TAG_CLEANUPS_FILENAME

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up taggit tags"

    def add_arguments(self, parser):
        parser.add_argument('--run', '-r',
                            action='store_true',
                            default=False)
        parser.add_argument('--load', '-l',
                            action='store_true',
                            default=False)
        parser.add_argument('--method', '-m',
                            default=False)
        parser.add_argument('--view',
                            action='store_true',
                            default=False,
                            help='view the staged tag cleanups')
        parser.add_argument('--dump', '-d',
                            action='store_true',
                            default=False,
                            help='dump staged tag cleanups and canonical name mappings to yaml files')

    def handle_load(self, restore_directory):
        path = restore_directory.joinpath(PENDING_TAG_CLEANUPS_FILENAME)
        print('Loading data from path {}'.format(str(path)))
        tag_cleanups = TagCleanup.load(path)
        TagCleanup.objects.bulk_create(tag_cleanups)

    def handle_method(self, method):
        if method == 'porter_stemmer':
            tag_cleanups = TagCleanup.find_groups_by_porter_stemmer()
        elif method == 'programming_language':
            tag_cleanups = TagCleanup.find_groups_by_platform_and_language()
        else:
            raise Exception('invalid method name')
        TagCleanup.objects.bulk_create(tag_cleanups)

    def handle_run(self):
        TagCleanup.objects.process()

    def handle_view(self):
        qs = TagCleanup.objects.filter(is_active=True)
        if qs.count() > 0:
            print('Tag Cleanups\n--------------------\n')
            for tag_cleanup in qs.iterator():
                print(tag_cleanup)
        else:
            print('No Pending Tag Cleanups!')

    def handle(self, *args, **options):
        run = options['run']
        load_directory = pathlib.Path('/shared/incoming/curator/tags')
        load = options['load']
        method = options.get('method')
        view = options['view']
        dump = options['dump']
        if run:
            self.handle_run()
        elif load:
            self.handle_load(load_directory)
        elif method:
            self.handle_method(method)
        elif dump:
            print('Dumping tag curation data to {}'.format(load_directory.joinpath(PENDING_TAG_CLEANUPS_FILENAME)))
            TagCleanup.objects.dump(load_directory.joinpath(PENDING_TAG_CLEANUPS_FILENAME))
        elif not view:
            raise Exception('restore directory, dump, method or view action must be specified')
        if view:
            self.handle_view()
