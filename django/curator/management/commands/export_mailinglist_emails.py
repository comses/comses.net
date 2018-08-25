import csv
import logging
import sys

import pytz
from dateutil.parser import parse as parse_date
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump active user emails for mailchimp import with filtered by is_active=True and optional date_joined --after=yyyy-mm-dd"

    def add_arguments(self, parser):
        parser.add_argument('--after', '-a', action='store', dest='after', default=None,
                            help='isoformat (yyyy-mm-dd) date the users were added e.g., --from 2018-03-15')

    def handle(self, *args, **options):
        UserModel = get_user_model()
        after_string = options['after']
        qs = UserModel.objects.filter(is_active=True)
        if after_string is not None:
            after_date = parse_date(after_string).replace(tzinfo=pytz.UTC)
            qs = qs.filter(date_joined__gte=after_date)
        csvf = csv.writer(sys.stdout)
        for user in qs:
            csvf.writerow(["{0} {1}".format(user.first_name, user.last_name), user.email])
