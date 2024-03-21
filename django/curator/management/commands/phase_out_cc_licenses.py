from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from core.utils import send_markdown_email
from library.models import CodebaseRelease
import os
import logging

logger = logging.getLogger(__name__)

# temp file to track which user ids have been sent emails
# in case of failure, we can resume from where we left off
SENT_EMAILS_FILE_PATH = os.path.join(settings.SHARE_DIR, "sent_cc_emails.txt")


class Command(BaseCommand):
    help = "provides some operations to help with phasing out Creative Commons licenses in the CML"

    def add_arguments(self, parser):
        parser.add_argument("operation", type=str, choices=["send_emails", "migrate"])
        parser.add_argument(
            "--test-user-id",
            type=int,
            required=False,
            help="If specified, only email or migrate the specified user's releases",
        )

    def handle(self, *args, **options):
        operation = options["operation"]
        if operation == "send_emails":
            self.send_emails(test_user_id=options["test_user_id"])
        if operation == "migrate":
            self.migrate(test_user_id=options["test_user_id"])

    def send_emails(self, test_user_id=None):
        sent_user_ids = self._read_sent_user_ids()

        # get all unique user ids that have submitted codebases with CC licenses
        releases_with_cc = CodebaseRelease.objects.filter(
            license__url__icontains="creativecommons.org"
        )
        unique_submitter_ids = (
            releases_with_cc.values_list("submitter", flat=True).distinct()
            if not test_user_id
            else [test_user_id]
        )
        for submitter_id in unique_submitter_ids:
            if submitter_id in sent_user_ids:
                logger.info(f"Email already sent to user {submitter_id}")
            else:
                user = User.objects.get(id=submitter_id)
                releases = releases_with_cc.filter(submitter=user)
                try:
                    # send email, if successful, append user id to temp file to mark as sent
                    send_markdown_email(
                        subject="CoMSES Net Codebase License Change",
                        body=self._get_email_body(user, releases),
                        to=[user.email],
                    )
                    with open(SENT_EMAILS_FILE_PATH, "a") as f:
                        f.write(f"{user.id}\n")
                    logger.info(f"Email sent to {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send email to {user.email}: {e}")

        # check if all submitters have been sent an email
        sent_user_ids = self._read_sent_user_ids()
        if not isinstance(unique_submitter_ids, set):
            unique_submitter_ids = set(unique_submitter_ids)
        unset_ids = unique_submitter_ids - sent_user_ids
        if unset_ids:
            logger.warning(
                f"Failed to send emails to the following user ids: {unset_ids}"
            )
        else:
            logger.info(
                f"""

====================================================================
All emails sent successfully, {SENT_EMAILS_FILE_PATH} can be removed
====================================================================
"""
            )

    def _read_sent_user_ids(self):
        # read temp file that tracks which user ids have been sent emails
        try:
            with open(SENT_EMAILS_FILE_PATH, "r") as f:
                return {int(line.strip()) for line in f}
        except FileNotFoundError:
            return set()

    def _get_email_body(self, user, releases):
        releases_list = ""
        for r in releases:
            releases_list += f"- {r.comses_permanent_url}edit\n"

        return f"""
Dear {user.member_profile.name},
        
We are writing to inform you that we are phasing out the use of Creative Commons licenses in the CoMSES Net Computational Model Library as CC licenses are not recommended for use in software. For more information regarding the reasoning behind this decision, please see the the following from the Creative Commons FAQ: https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software.

We have identified the following codebases submitted by you that are currently licensed under a Creative Commons license:

{releases_list}

FIXME: what else? ask to change license? with or without migrating to a default in X days?

Sincerely,
The CoMSES Net Team
        """

    def migrate(self, test_user_id=None):
        pass
