from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import MemberProfile, User, Institution, ComsesGroups


class Command(BaseCommand):
    help = "Initialize DB for use with frontend integration tests."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            pk=settings.TEST_USER_ID,
            username=settings.TEST_USERNAME,
            defaults=dict(first_name="Test", last_name="User", email="a@b.com"),
        )
        ComsesGroups.initialize()
        user.set_password(settings.TEST_BASIC_AUTH_PASSWORD)
        user.save()
        mp, created = MemberProfile.objects.get_or_create(user=user)
        mp.institution = Institution.objects.get_or_create(
            name="ASU", url="https://www.asu.edu"
        )[0]
        mp.save()
        ea, created = EmailAddress.objects.get_or_create(user=user, email=user.email)
        ea.verified = True
        ea.set_as_primary(conditional=True)
        ea.save()
