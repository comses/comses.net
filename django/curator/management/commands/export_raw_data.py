import logging
import os

from django.core.management.base import BaseCommand
from django.db import connection
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export unaggregated raw data as CSV for a given time period"
    directory = "/shared/data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            help="isoformat start date (yyyy-mm-dd) e.g., --from 2018-03-15",
            default=None,
        )
        parser.add_argument(
            "--to",
            help="isoformat end date (yyyy-mm-dd) e.g., --to 2018-06-01. Blank defaults to today.",
            default=None,
        )
        parser.add_argument(
            "--directory",
            "-d",
            help="directory to place data in relative to the CMS container",
            default="/shared/data",
        )
        parser.add_argument(
            "--selections",
            "-s",
            help="selected data tables to dump ",
            default="codebase,download,release,user",
        )

    def _export(self, filename, table_name=None, select_statement=None):
        if not any([table_name, select_statement]):
            raise ValueError(
                "Must pass a valid table_name or select_statement parameter"
            )
        if select_statement is None:
            select_statement = f"SELECT * FROM {table_name} ORDER BY id"
        destination_path = Path(self.directory) / filename
        with connection.cursor() as cursor:
            cursor.execute(
                f"COPY ({select_statement}) TO '{destination_path}' WITH CSV HEADER"
            )

    def export_codebases(self):
        self._export("codebases.csv", "library_codebase")

    def export_releases(self):
        self._export("releases.csv", "library_codebaserelease")

    def export_downloads(self):
        self._export("downloads.csv", "library_codebasereleasedownload")

    def export_users(self):
        join_user_member_profile_select = """
        SELECT 
        u.id, u.last_login, u.is_superuser, u.username, u.first_name, u.last_name, u.email, u.date_joined, u.is_active,
        mp.affiliations, mp.bio, mp.degrees, mp.personal_url, mp.professional_url, mp.research_interests, mp.timezone,
        mp.industry 
        FROM auth_user u INNER JOIN core_memberprofile mp ON u.id=mp.user_id
        ORDER BY u.id
        """
        self._export("users.csv", select_statement=join_user_member_profile_select)

    def handle(self, *args, **options):
        """
        exports raw tabular data into postgres
        """
        # FIXME: currently unused timerange filters, export all the data
        from_date_string = options.get("from")
        to_date_string = options.get("to")
        self.directory = options["directory"]
        selections = options["selections"].split(",")
        os.makedirs(self.directory, exist_ok=True)
        os.chmod(self.directory, 0o777)
        if "codebase" in selections:
            self.export_codebases()
        if "release" in selections:
            self.export_releases()
        if "download" in selections:
            self.export_downloads()
        if "user" in selections:
            self.export_users()
