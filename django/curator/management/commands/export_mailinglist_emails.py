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
    help = """Dump active user emails for mailchimp import with filtered by is_active=True
              and optional date_joined --after=yyyy-mm-dd"""

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        # exclude django-guardian AnonymousUser
        User = get_user_model()
        anonymous_user = User.get_anonymous()
        criteria = {"is_active": True}
        after_string = options["after"]
        if after_string is not None:
            after_date = parse_date(after_string).replace(tzinfo=pytz.UTC)
            criteria.update(date_joined__gte=after_date)
        full_member = options["full_member_only"]
        qs = (
            ComsesGroups.FULL_MEMBER.users(**criteria)
            if full_member
            else User.objects.filter(**criteria).exclude(id=anonymous_user.id)
        )
        csv_writer = csv.writer(sys.stdout)
        csv_writer.writerow(
            ["First name", "Last name", "Affiliation", "Affil URL", "Email"]
        )
        for user in qs:
            csv_writer.writerow(
                [
                    user.first_name,
                    user.last_name,
                    user.member_profile.primary_affiliation_name,
                    user.member_profile.primary_affiliation_url,
                    user.email,
                ]
            )
