from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from pathlib import Path

from core.utils import send_markdown_email
from library.models import CodebaseRelease
import logging

logger = logging.getLogger(__name__)

# temp file to track which user ids have been sent emails
# in case of failure, we can resume from where we left off
SENT_EMAILS_FILE_PATH = Path(settings.SHARE_DIR, "sent_cc_emails.txt")

CC_LICENSE_CHANGE_URL = settings.BASE_URL + reverse("library:cc-license-change")


class Command(BaseCommand):
    help = """
    Sends an email to all users who have submitted codebase releases
    that are currently licensed under a Creative Commons license
    """

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
        releases_with_cc = CodebaseRelease.objects.with_cc_license()
        unique_submitter_ids = set(
            releases_with_cc.values_list("submitter", flat=True).distinct()
            if not test_user_id
            else [test_user_id]
        )
        users = User.objects.filter(id__in=unique_submitter_ids)
        user_emails = [user.email for user in users if user.id not in sent_user_ids]
        try:
            # send email, if successful, append user id to temp file to mark as sent
            if user_emails:
                send_markdown_email(
                    to=[settings.EDITOR_EMAIL],
                    subject="CoMSES Net Codebase License Change",
                    body=self._get_email_body(),
                    bcc=[user_emails],
                )
                with SENT_EMAILS_FILE_PATH.open("a") as f:
                    f.write("\n".join(map(str, unique_submitter_ids)))
            else:
                logger.info("No emails needed to be sent: %s", user_emails)
        except Exception as e:
            logger.error("Failed to send email", e)

        # check if all submitters have been sent an email
        sent_user_ids = self._read_sent_user_ids()
        unset_ids = unique_submitter_ids - sent_user_ids
        if unset_ids:
            logger.warning(
                f"Failed to send emails to the following user ids: {unset_ids}"
            )
        else:
            logger.info(f"""

====================================================================
All emails sent successfully, {SENT_EMAILS_FILE_PATH} can be removed
====================================================================

""")

    def _read_sent_user_ids(self):
        # read temp file that tracks which user ids have been sent emails
        try:
            with SENT_EMAILS_FILE_PATH.open("r") as f:
                return {int(line.strip()) for line in f}
        except FileNotFoundError:
            return set()

    def _get_email_body(self):
        return f"""
Dear CoMSES Member,
        
We are planning to phase out Creative Commons licenses in the CoMSES Model Library due to their [unsuitability for software](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software) and have determined that one or more of your submissions to the CoMSES Computational Model Library currently use a Creative Commons license. In order to ensure that your published computational models are properly licensed for reuse, we strongly urge to consider selecting an alternate OSI-approved open source license for your computational models. 

We have set up a straightforward process to transition all of your submissions at once to an appropriate software license. You can access this service at the following link (you will need to sign in to comses.net first):

    [{CC_LICENSE_CHANGE_URL}]({CC_LICENSE_CHANGE_URL})

Thank you for helping us make model software more accessible and reusable, and do not hesitate to contact us if you have any questions or require further assistance.

Sincerely,
The CoMSES Net Team
        """
