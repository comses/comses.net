from django.core.management.base import BaseCommand
from core.models import MemberProfile, User, Institution
from allauth.account.models import EmailAddress
from ..common import TEST_BASIC_AUTH_PASSWORD

class Command(BaseCommand):
    help = "Initialize DB for use with frontend integration tests."

    def handle(self, *args, **options):
        u = User.objects.get_or_create(
            username='__TEST_USER__',
            defaults=dict(first_name='Test', last_name='User', email='a@b.com'))[0]
        u.set_password(TEST_BASIC_AUTH_PASSWORD)
        u.save()
        mp = MemberProfile.objects.get(user=u)
        mp.institution = Institution.objects.get_or_create(name='ASU', url='https://www.asu.edu')[0]
        mp.save()
        ea = EmailAddress.objects.get_or_create(user=u)[0]
        ea.verified = True
        ea.set_as_primary(conditional=True)
        ea.save()
