import logging
import os

from django.conf import settings
from django.db import connections
from django.test import TransactionTestCase
from invoke import Context

from core.models import Event, Job
from core.tests.base import (
    UserFactory,
    initialize_test_shared_folders,
    destroy_test_shared_folders,
)
from curator.invoke_tasks.borg import _restore as restore_archive, backup
from core.tests.base import EventFactory, JobFactory
from library.fs import import_archive
from library.models import Codebase
from library.tests.base import CodebaseFactory, TEST_SAMPLES_DIR

logger = logging.getLogger(__name__)


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def setUpModule():
    initialize_test_shared_folders()


class DumpRestoreTestCase(TransactionTestCase):
    databases = {"default", "dump_restore"}

    def setUp(self):
        user_factory = UserFactory()
        self.user = user_factory.create()

        event_factory = EventFactory(submitter=self.user)
        self.event = event_factory.create()

        job_factory = JobFactory(submitter=self.user)
        self.job = job_factory.create()

        codebase_factory = CodebaseFactory(submitter=self.user)
        self.codebase = codebase_factory.create()
        self.release = self.codebase.create_release()
        fs_api = self.release.get_fs_api()
        import_archive(
            codebase_release=self.release,
            nested_code_folder_name=TEST_SAMPLES_DIR / "archives" / "nestedcode",
            fs_api=fs_api,
        )

    def test_dump_and_restore(self):
        # Backup the test files and the test database
        ctx = Context()
        backup(ctx)

        # Restore the files to their original location and the test database dump to the dump_restore database
        extractor_dir = os.path.join(settings.SHARE_DIR, "extraction")
        os.makedirs(extractor_dir, exist_ok=True)
        restore_archive(
            ctx,
            repo=settings.BORG_ROOT,
            archive=None,
            working_directory=extractor_dir,
            target_database="dump_restore",
        )

        connections._connections.dump_restore.close()
        self.assertEqual(Codebase.objects.using("dump_restore").first(), self.codebase)
        self.assertEqual(Event.objects.using("dump_restore").first(), self.event)
        self.assertEqual(Job.objects.using("dump_restore").first(), self.job)
        fs_api = self.release.get_fs_api()
        contents = fs_api.list_sip_contents()
        self.assertTrue(contents["contents"])

    def tearDown(self):
        for c in self.user.codebases.all():
            c.releases.all().delete()
            c.delete()
        self.user.delete()


def tearDownModule():
    destroy_test_shared_folders()
