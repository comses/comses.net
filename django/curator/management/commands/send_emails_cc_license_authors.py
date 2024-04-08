from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from core.utils import send_markdown_email
from library.models import CodebaseRelease
import os
import logging

logger = logging.getLogger(__name__)

# temp file to track which user ids have been sent emails
# in case of failure, we can resume from where we left off
SENT_EMAILS_FILE_PATH = os.path.join(settings.SHARE_DIR, "sent_cc_emails.txt")

CC_LICENSE_CHANGE_URL = settings.BASE_URL + reverse("library:cc-license-change")


class Command(BaseCommand):
    help = "Sends an email to all users who have submitted codebase releases currently licensed under a Creative Commons license"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-user-id",
            type=int,
            required=False,
            help="If specified, only email the specified user about their releases",
        )

    def handle(self, *args, **options):
        self.send_emails(test_user_id=options["test_user_id"])

    def send_emails(self, test_user_id=None):
        sent_user_ids = self._read_sent_user_ids()

        # get all unique user ids that have submitted codebases with CC licenses
        releases_with_cc = CodebaseRelease.objects.filter(
            license__name__istartswith="CC"
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
                        body=self._get_email_body(user),
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

    def _get_email_body(self, user):
        return f"""
Dear {user.member_profile.name},
        
We are writing to inform you that we are phasing out the use of Creative Commons licenses in the CoMSES Model Library due to their [unsuitability for software](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software) and have identified one or more of your submissions that currently use such a license. In order to ensure that software archived with us is properly licensed for reuse, we are asking authors to relicense their models and have set up a straightforward process to transition all of your submissions at once to an appropriate software license. You can access this service at the following link:

[{CC_LICENSE_CHANGE_URL}]({CC_LICENSE_CHANGE_URL})

Thank you for helping us make model software more accessible and reusable, and do not hesitate to contact us if you have any questions or require further assistance.

Sincerely,
The CoMSES Net Team
        """
