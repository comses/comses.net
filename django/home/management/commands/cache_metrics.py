import logging

from django.core.management.base import BaseCommand

from home.metrics import Metrics

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """generate metrics and cache in redis"""

    def add_arguments(self, parser):
        """
        this uses argparse https://docs.python.org/3/library/argparse.html
        parser.add_argument(
            "--full-member-only", "-u", action="store_true", dest="full_member_only"
        )
        parser.add_argument(
            "--after",
            "-a",
            action="store",
            dest="after",
            default=None,
            help="yyyy-mm-dd date to filter users e.g., --after=2018-03-15",
        )
        """
        pass

    def handle(self, *args, **options):
        metrics = Metrics()
        logger.debug("caching all metrics")
        metrics.cache_all()
