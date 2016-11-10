import json

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from wagtail.wagtailcore.models import Site
from ...models import HomePage


class Command(BaseCommand):
    help = "My shiny new management command."

    def add_arguments(self, parser):
        parser.add_argument('config_file')

    @staticmethod
    def read_config(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)

    def handle(self, *args, **options):
        config = self.read_config(options['config_file'])

        User.objects.create_superuser()
        Site.objects.filter(id=1) \
            .update(hostname=config['hostname'], port=config['port'], site_name=config['site_name'])
