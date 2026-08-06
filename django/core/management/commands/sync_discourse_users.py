import time

from django.core.management.base import BaseCommand

from core.models import MemberProfile
from home.signals import sync_discourse_user


class Command(BaseCommand):
    help = "Synchronize CoMSES users to Discourse via DiscourseConnect sync_sso"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List users that would be synced without calling Discourse.",
        )
        parser.add_argument(
            "--username",
            action="append",
            dest="usernames",
            help="Sync a specific username. May be passed multiple times.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of users to process.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Seconds to wait between Discourse requests. Defaults to 1.0.",
        )

    def get_queryset(self, usernames=None, limit=None):
        members = MemberProfile.objects.public()
        if usernames:
            members = members.filter(user__username__in=usernames)
        if limit:
            members = members[:limit]
        return members

    def handle(self, *args, **options):
        members = self.get_queryset(options.get("usernames"), options.get("limit"))
        total = members.count()
        synced = 0
        failed = 0

        if options["dry_run"]:
            self.stdout.write(f"Would sync {total} user(s) to Discourse")
            for member in members:
                self.stdout.write(f"DRY RUN {member.username}")
            return

        for index, member in enumerate(members, start=1):
            if index > 1 and options["delay"] > 0:
                time.sleep(options["delay"])

            self.stdout.write(f"Syncing {member.username} ({index}/{total})")
            if sync_discourse_user(member.user):
                synced += 1
                self.stdout.write(self.style.SUCCESS(f"Synced {member.username}"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Failed {member.username}"))

        self.stdout.write(f"Finished Discourse sync: {synced} synced, {failed} failed")
