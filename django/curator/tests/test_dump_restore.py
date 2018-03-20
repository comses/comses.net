from django.contrib.auth.models import User
from django.db import connections
from django.test import TestCase

from core.models import Job
from core.tests.base import UserFactory
from home.tests.base import EventFactory, JobFactory
from library.fs import import_archive
from library.models import Codebase
from library.tests.base import CodebaseFactory


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class DumpRestoreTestCase(TestCase):

    def test_dump_and_restore(self):
        with connections['dump_restore'].cursor() as c:
            c.execute("select * from information_schema.tables where table_schema = 'public'")
            results = dictfetchall(c)
            self.assertEqual(results[0]['table_name'], 'django_migrations')
