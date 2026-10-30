"""Application-owned synthetic fixtures. Never imports or anonymizes source data."""

import hashlib
import io
import re
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import connection, transaction
from guardian.utils import get_anonymous_user
from library.fs import FileCategories
from library.models import OS, Codebase, Contributor, License, ProgrammingLanguage, ReleaseLanguage

POLICY_VERSION = "synthetic-v1"
PUBLIC_MODELS = 12
MODEL_SOURCE = b'''"""Synthetic logistic growth model; no external dependencies or data."""
import csv
from pathlib import Path

population = 10.0
for step in range(10):
    population += 0.2 * population * (1 - population / 100)
    print(step, round(population, 4))
'''
DOCUMENTATION = "# Synthetic recovery fixture\n\nRun `python model.py`. Data is synthetic.\n"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight(database, root):
    """Refuse existing schemas/storage instead of attempting in-place sanitization."""
    if settings.SETTINGS_MODULE != "core.settings.seed":
        raise CommandError("Use core.settings.seed with disposable database and storage.")
    if database != connection.settings_dict["NAME"] or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", database):
        raise CommandError("Database confirmation does not match a synthetic-seed database.")
    root = Path(root)
    if str(root) != settings.SHARE_DIR or not root.is_absolute() or root.resolve() != root:
        raise CommandError("Storage confirmation must match the physical seed root (no symlinks).")
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise CommandError("Seed storage must be absent or empty; use a fresh candidate after failure.")
    for setting, suffix in (
        ("LIBRARY_ROOT", "library"),
        ("MEDIA_ROOT", "media"),
        ("REPOSITORY_ROOT", "repository"),
        ("BACKUP_ROOT", "backups"),
    ):
        if Path(getattr(settings, setting)) != root / suffix:
            raise CommandError(f"{setting} is outside the confirmed seed layout.")
    if database in {"postgres", "template0", "template1"}:
        raise CommandError("System databases cannot be seed targets.")
    if connection.introspection.table_names(include_views=True):
        raise CommandError("Seed database must have no tables; existing databases are never sanitized.")
    # Introspection follows search_path; reject data in other schemas too. This
    # read-only catalog query is necessary before any ORM tables exist.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema' "
            "AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S'))"
        )
        if cursor.fetchone()[0]:
            raise CommandError("Seed database contains relations outside the default schema.")
    return root


def inventory(root):
    records = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise CommandError("Unexpected symlink in synthetic fixture storage.")
        if path.is_file():
            records.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def add_file(api, category, name, content):
    stream = io.BytesIO(content)
    stream.name = name
    messages = api.add(category, stream)
    if messages.has_errors:
        raise CommandError(f"Synthetic fixture upload failed: {category.name}/{name}")
    path = api.sip_contents_dir / category.name / name
    if sha256(path) != hashlib.sha256(content).hexdigest():
        raise CommandError("Synthetic file bytes changed during upload.")


def release_fixture(codebase, version, license, language, second_author, data, public=True):
    release = codebase.create_release(version_number=version, share_uuid=None)
    release.license = license
    release.os = OS.PLATFORM_INDEPENDENT
    release.release_notes = f"Synthetic fixture {version}; café / 模型."
    if not release.release_languages.exists():
        ReleaseLanguage.objects.create(release=release, programming_language=language)
    release.add_contributor(second_author)
    api = release.get_fs_api()
    add_file(api, FileCategories.code, "model.py", MODEL_SOURCE + f"\n# version {version}\n".encode())
    add_file(api, FileCategories.docs, "README.md", DOCUMENTATION.encode())
    add_file(api, FileCategories.data, "input.csv", data)
    release.save(defer_fs=False)
    if public:
        # Uses the real validation/archive path. The seed settings hold any queued
        # integration work in process-local memory; no consumer is ever started.
        release.publish()
        with ZipFile(api.archivepath) as archive:
            if archive.testzip() is not None:
                raise CommandError("Synthetic archive failed CRC verification.")
            names = set(archive.namelist())
            for category, name in (("code", "model.py"), ("docs", "README.md"), ("data", "input.csv")):
                relative = f"{category}/{name}"
                matches = [name for name in names if name.endswith("/" + relative) or name == relative]
                if len(matches) != 1 or archive.read(matches[0]) != (api.sip_contents_dir / relative).read_bytes():
                    raise CommandError("Synthetic archive does not match its fixture files.")
    return {
        "codebase": codebase.identifier,
        "release_id": release.pk,
        "version": version,
        "status": release.status,
        "doi": release.doi,
        "detail_path": release.get_absolute_url(),
        "archive": str(api.archivepath.relative_to(settings.SHARE_DIR)) if public else None,
        "archive_sha256": sha256(api.archivepath) if public else None,
        "contributors": list(release.codebase_contributors.order_by("index").values_list("contributor_id", flat=True)),
    }


@transaction.atomic
def build_fixtures(large_data_mib):
    """Called only after a fresh schema was migrated; no destructive cleanup/retry."""
    User = get_user_model()
    anonymous = get_anonymous_user()
    if User.objects.exclude(pk=anonymous.pk).exists() or Codebase.objects.exists() or Contributor.objects.exists():
        raise CommandError("Unexpected accounts/content in the fresh migration baseline.")
    # django-guardian creates this framework identity during post_migrate.
    # It is not a fixture login and must not carry usable authentication state.
    if anonymous.has_usable_password() or anonymous.is_staff or anonymous.is_superuser:
        raise CommandError("Unexpected credentials on the anonymous framework identity.")
    anonymous.is_active = False
    anonymous.save(update_fields=["is_active"])
    for setting in ("LIBRARY_ROOT", "MEDIA_ROOT", "REPOSITORY_ROOT", "BACKUP_ROOT"):
        Path(getattr(settings, setting)).mkdir(parents=True, exist_ok=True)
    users = []
    for role in ("owner", "unrelated"):
        user = User(
            username=f"seed-{role}",
            email=f"{role}@example.invalid",
            first_name="Synthetic",
            last_name=role.title(),
            is_active=False,
        )
        user.set_unusable_password()
        user.save()
        users.append(user)
    second_author = Contributor.objects.create(given_name="Zoë", family_name="模型", type="person")
    license, _ = License.objects.get_or_create(
        name="CC0-1.0", defaults={"url": "https://creativecommons.org/publicdomain/zero/1.0/"}
    )
    language, _ = ProgrammingLanguage.objects.get_or_create(name="Python")
    data = b"step,population\n0,10\n1,11.8\n"
    # Deterministic, nontrivially compressible synthetic CSV; bounded by CLI validation.
    large = bytearray(b"row,value\n")
    index = 0
    while len(large) < large_data_mib * 1024 * 1024:
        large.extend(f"{index},{hashlib.sha256(str(index).encode()).hexdigest()}\n".encode())
        index += 1
    releases = []
    for number in range(1, PUBLIC_MODELS + 2):
        public = number <= PUBLIC_MODELS
        identifier = f"seed-public-{number:02d}" if public else "seed-private"
        codebase = Codebase.objects.create(
            identifier=identifier,
            uuid=UUID(int=number),
            title=f"Synthetic recovery {identifier}",
            description="Synthetic recovery fixture, not a real research publication.",
            submitter=users[0],
        )
        releases.append(
            release_fixture(
                codebase,
                "1.0.0",
                license,
                language,
                second_author,
                bytes(large) if number == 2 else data,
                public=public,
            )
        )
        if number == 1:
            releases.append(release_fixture(codebase, "1.1.0", license, language, second_author, data))
    if any(
        user.has_usable_password() or user.is_active or user.is_staff or user.is_superuser
        for user in User.objects.all()
    ):
        raise CommandError("Seed contains an enabled account or usable credentials.")
    if Codebase.objects.filter(doi__isnull=False).exists():
        raise CommandError("Synthetic fixtures must not claim a DOI.")
    from library.models import CodebaseRelease

    if (
        CodebaseRelease.objects.filter(share_uuid__isnull=False).exists()
        or CodebaseRelease.objects.filter(doi__isnull=False).exists()
    ):
        raise CommandError("Synthetic fixtures must not contain share capabilities or DOIs.")
    return {
        "policy": POLICY_VERSION,
        "releases": releases,
        "public_codebase_identifiers": [f"seed-public-{n:02d}" for n in range(1, PUBLIC_MODELS + 1)],
        "private_codebase_identifiers": ["seed-private"],
        "large_input_bytes": len(large),
        "coverage": [
            "model-source",
            "documentation",
            "data",
            "multiple-versions",
            "private",
            "unicode",
            "pagination-corpus",
        ],
        "limitations": [
            "synthetic only; no production recovery point",
            "larger-fixture representativeness requires operator review",
            "no registered DOIs, real reviews, SSO, or enabled logins",
            "HTTP authorization and search/index checks require a separate restore drill",
        ],
    }
