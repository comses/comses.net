import logging
import os

from django.core.management.base import BaseCommand
from django.db import connection
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = """Export unaggregated raw data as CSV files for a given time period."""
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
            help="selected data tables to dump: codebase, download, release, user",
            default="codebase,download,release,user",
        )

    def _export(
        self,
        filename,
        table_name=None,
        select_statement=None,
        from_date=None,
        end_date=None,
    ):
        """
        Export data from a table or a select statement to a CSV file
        """
        if not any([table_name, select_statement]):
            raise ValueError(
                "Must pass a valid table_name or select_statement parameter"
            )
        if select_statement is None:
            where_clause = ""
            if all([from_date, end_date]):
                where_clause = f"WHERE date_created >= '{from_date}' AND date_created <= '{end_date}'"
            select_statement = f"""
            SELECT * FROM {table_name}
            {where_clause}
            ORDER BY id
            """
        destination_path = Path(self.directory) / filename
        with connection.cursor() as cursor:
            cursor.execute(
                f"COPY ({select_statement}) TO '{destination_path}' WITH CSV HEADER"
            )

    def export_codebases(self, **kwargs):
        self._export("codebases.csv", "library_codebase", **kwargs)

    def export_releases(self, **kwargs):
        self._export("releases.csv", "library_codebaserelease", **kwargs)

    def export_downloads(self, **kwargs):
        self._export("downloads.csv", "library_codebasereleasedownload", **kwargs)

    def export_users(self, from_date=None, end_date=None):
        where_clause = ""
        if all([from_date, end_date]):
            where_clause = f"WHERE u.date_joined >= '{from_date}' AND u.date_joined <= '{end_date}'"
        join_user_member_profile_select = f"""
        SELECT 
        u.id, u.last_login, u.is_superuser, u.username, u.first_name, u.last_name, u.email, u.date_joined, u.is_active,
        mp.affiliations, mp.bio, mp.degrees, mp.personal_url, mp.professional_url, mp.research_interests, mp.timezone,
        mp.industry 
        FROM auth_user u INNER JOIN core_memberprofile mp ON u.id=mp.user_id
        {where_clause}
        ORDER BY u.id
        """
        self._export("users.csv", select_statement=join_user_member_profile_select)

    def handle(self, *args, **options):
        """
        exports raw tabular data into postgres
        """
        from_date_string = options.get("from")
        to_date_string = options.get("to")
        self.directory = options["directory"]
        selections = options["selections"].split(",")
        date_constraints = {"from_date": from_date_string, "end_date": to_date_string}
        os.makedirs(self.directory, exist_ok=True)
        os.chmod(self.directory, 0o777)
        if "codebase" in selections:
            self.export_codebases(**date_constraints)
        if "release" in selections:
            self.export_releases(**date_constraints)
        if "download" in selections:
            self.export_downloads(**date_constraints)
        if "user" in selections:
            self.export_users(**date_constraints)
