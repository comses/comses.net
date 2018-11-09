import csv
import logging
import sys

import pytz
from dateutil.parser import parse as parse_date
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import ComsesGroups

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump active user emails for mailchimp import with filtered by is_active=True and optional date_joined --after=yyyy-mm-dd"

    def add_arguments(self, parser):
        parser.add_argument('--full-member-only', '-u', action='store_true', dest='full_member_only')
        parser.add_argument('--after', '-a', action='store', dest='after', default=None,
                            help='yyyy-mm-dd date after which users were added e.g., --after=2018-03-15')

    def handle(self, *args, **options):
        criteria = {'is_active': True}
        after_string = options['after']
        if after_string is not None:
            after_date = parse_date(after_string).replace(tzinfo=pytz.UTC)
            criteria.update(date_joined__gte=after_date)
        full_member = options['full_member_only']
        qs = ComsesGroups.FULL_MEMBER.users(**criteria) if full_member else get_user_model().objects.filter(**criteria)
        cvs_writer = csv.writer(sys.stdout)
        for user in qs:
            cvs_writer.writerow([user.first_name, user.last_name, user.member_profile.institution, user.email])
