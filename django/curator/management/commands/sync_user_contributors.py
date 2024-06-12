import logging

from django.core.management.base import BaseCommand

from library.models import Contributor


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Synchronize user metadata with contributor metadata for testing / development purposes."""

    def handle(self, *args, **options):
        # cannot update local model attributes to a join field attribute; this doesn't work:
        # Contributor.objects.filter(user__isnull=False).update(given_name=F('user__first_name'), ...)
        # see
        # https://docs.djangoproject.com/en/dev/topics/db/queries/#updating-multiple-objects-at-once
        # for more details
        for contributor in Contributor.objects.select_related("user").filter(
            user__isnull=False
        ):
            user = contributor.user
            contributor.given_name = user.first_name
            contributor.family_name = user.last_name
            contributor.email = user.email
            contributor.json_affiliations = user.member_profile.affiliations
            contributor.save()
