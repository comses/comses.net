import argparse
import logging

from django.core.management.base import BaseCommand

from library.models import Contributor


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Synchronize user metadata with contributor metadata for testing / development purposes."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action=argparse.BooleanOptionalAction,
            help="Force the update of all contributors metadata to current User metadata (first_name, last_name, email, json_affiliations).",
            default=False,
        )

    def should_update(self, existing, candidate):
        if not existing:
            return True
        return candidate and existing != candidate

    def handle(self, *args, **options):
        # cannot update local model attributes to a join field attribute; this doesn't work:
        # Contributor.objects.filter(user__isnull=False).update(given_name=F('user__first_name'), ...)
        # see
        # https://docs.djangoproject.com/en/dev/topics/db/queries/#updating-multiple-objects-at-once
        # for more details
        force = options["force"]
        for contributor in Contributor.objects.select_related("user").filter(
            user__isnull=False
        ):
            user = contributor.user
            if force or self.should_update(contributor.given_name, user.first_name):
                contributor.given_name = user.first_name
            if force or self.should_update(contributor.family_name, user.last_name):
                contributor.family_name = user.last_name
            if force or self.should_update(contributor.email, user.email):
                contributor.email = user.email
            member_profile_affiliations = user.member_profile.affiliations
            if force or self.should_update(
                contributor.json_affiliations, member_profile_affiliations
            ):
                contributor.json_affiliations = member_profile_affiliations
            contributor.save()
