from django.core.management.base import BaseCommand

from robots.models import Rule, Url


class Command(BaseCommand):
    help = "Setup robots.txt Rules"

    def add_arguments(self, parser):
        parser.add_argument('--allow',
                            dest='allow',
                            action='store_true',
                            help='Create a robots.txt Rule to allow all crawling.'
                            )
        parser.add_argument('--no-allow',
                            dest='allow',
                            action='store_false',
                            help='Create a robots.txt Rule to deny all crawling.')
        parser.set_defaults(allow=True)

    def handle(self, *args, **options):
        allow_all = options['allow']
        rule, created = Rule.objects.get_or_create(robot='*')
        if allow_all:
            # consider using Sitemap for Rule creation later
            pass
        else:
            rule.disallowed.clear()
            rule.disallowed.add(Url.objects.create(pattern='/'))
