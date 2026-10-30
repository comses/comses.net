import json
import re
from datetime import UTC, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core import synthetic_seed
from django.core.management import call_command


class Command(BaseCommand):
    help = "Build an unapproved synthetic seed in an empty, isolated database and shared root."
    requires_system_checks = []  # The schema does not exist yet.

    def add_arguments(self, parser):
        parser.add_argument("--confirm-database", required=True)
        parser.add_argument("--confirm-root", required=True)
        parser.add_argument("--release", required=True, help="Exact application commit attested by the caller")
        parser.add_argument("--large-data-mib", type=int, default=8)
        parser.add_argument("--apply", action="store_true", help="Default is read-only preflight")

    def handle(self, *args, **options):
        if not re.fullmatch(r"[0-9a-f]{40}", options["release"]):
            raise CommandError("--release must be a full lowercase Git commit SHA.")
        if not 1 <= options["large_data_mib"] <= 64:
            raise CommandError("--large-data-mib must be between 1 and 64.")
        root = synthetic_seed.preflight(options["confirm_database"], options["confirm_root"])
        if not options["apply"]:
            self.stdout.write("Preflight passed; no fixtures created. Candidate publication remains unapproved.")
            return
        # This narrow PostgreSQL advisory lock serializes builders targeting the
        # same database, even when callers supply different filesystem roots.
        # Content queries and writes continue to use the ORM.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(current_database()), 73633)")
            if not cursor.fetchone()[0]:
                raise CommandError("Another seed builder owns this database.")
        try:
            self.build(root, options)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(current_database()), 73633)")

    def build(self, root, options):
        synthetic_seed.preflight(options["confirm_database"], options["confirm_root"])
        root.mkdir(parents=True, exist_ok=True)
        report_path = root / "seed-build.json"
        report = {
            "schema": 1,
            "kind": "synthetic-candidate",
            "status": "building",
            "publication_approved": False,
            "recovery_accepted": False,
            "release_attested_by_caller": options["release"],
            "builder_sha256": synthetic_seed.sha256(synthetic_seed.__file__),
            "policy": synthetic_seed.POLICY_VERSION,
            "database": options["confirm_database"],
            "root": str(root),
            "started_at": datetime.now(UTC).isoformat(),
        }
        # Exclusive creation also protects an accidentally shared filesystem root.
        with report_path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
        try:
            (root / "uploads").mkdir()
            call_command("migrate", interactive=False, verbosity=0)
            call_command("check", verbosity=0)
            report.update(synthetic_seed.build_fixtures(options["large_data_mib"]))
            report["files"] = {
                category: synthetic_seed.inventory(root / category) for category in ("library", "media", "repository")
            }
            report["status"] = "built-unapproved"
        except Exception as exc:
            report["status"] = "failed"
            report["failure_type"] = type(exc).__name__
            # Do not serialize exception text: database errors can contain data.
            raise CommandError(
                "Seed build failed; retain its report and use a fresh database/root after investigation."
            ) from exc
        finally:
            report["finished_at"] = datetime.now(UTC).isoformat()
            temporary = report_path.with_suffix(".tmp")
            with temporary.open("x", encoding="utf-8") as output:
                json.dump(report, output, indent=2, ensure_ascii=False)
                output.write("\n")
            temporary.replace(report_path)
        self.stdout.write(f"Built unapproved synthetic candidate; evidence: {report_path}")
