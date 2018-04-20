import time
from core.discourse import create_discourse_user
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from library.models import CodebaseRelease


class Command(BaseCommand):
    help = "Copy CoMSES users to discourse"

    @staticmethod
    def check_discourse_user_response(response, user):
        data = response.json()
        # if there are errors creating the user account move on to the next
        # these errors should about the email or username already existing or the username being too long
        if not data.get('success', False):
            print('skipping {} {}'.format(user, data.get('errors')))
            return None
        else:
            print('added user {}'.format(user))
            return user

    def handle(self, *args, **options):
        # getting a list of all users in discourse api is difficult so try to add each one
        users = User.objects.exclude(username__in=['AnonymousUser', '__test_user__']) \
            .filter(is_active=True).order_by('username')
        added_users = []
        for user in users:
            # hack to avoid 429 response from discourse
            time.sleep(1)
            
            print('\nsyncing user {}'.format(user))
            response = create_discourse_user(user)
            if not (200 <= response.status_code < 300):
                print('bad reponse for user {} {}'.format(user, response.status_code))
                print(response.content)

                continue
            user = self.check_discourse_user_response(response, user)
            if user:
                added_users.append(user)

        print('\nAdded Users')
        for added_user in added_users:
            print(added_user)