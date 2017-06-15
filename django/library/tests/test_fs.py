import io
import os
import shutil
import tarfile
import zipfile

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from ..models import CodebaseRelease, Codebase


class FsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src_content = 'print("hello")'
        cls.data_content = 'town,pop\nfoo,2000'

    def setUp(self):
        submitter = User.objects.first()
        self.codebase = Codebase.objects.create(title='codebase', submitter=submitter)
        self.codebase_release = CodebaseRelease.objects.create(
            identifier='0.0.0',
            version_number='0.0.0',
            submitter=submitter,
            codebase=self.codebase)

    def test_zipfile_saving(self):
        zip_file = io.BytesIO()
        with zipfile.ZipFile(zip_file, 'a') as z:
            z.writestr('main.py', self.src_content)

        archive_name = 'zip.zip'
        zip_file.name = archive_name
        zip_file.seek(0)
        self.codebase_release.add_src_upload(zip_file)

        with open(str(self.codebase_release.get_library_path('src', 'main.py')), 'r') as f:
            self.assertEqual(f.read(), self.src_content)

    def test_tarfile_saving(self):
        tar_file = io.BytesIO()
        with tarfile.TarFile(fileobj=tar_file, mode='w') as t:
            main_file_content = bytes(self.src_content, 'utf8')
            info = tarfile.TarInfo('main.txt')
            info.size = len(main_file_content)
            t.addfile(info, io.BytesIO(main_file_content))

        archive_name = 'tar.tar'
        tar_file.name = archive_name
        tar_file.seek(0)
        self.codebase_release.add_data_upload(tar_file)

        with open(str(self.codebase_release.get_library_path('data', 'main.txt')), 'r') as f:
            self.assertEqual(f.read(), self.src_content)

    def test_file_saving(self):
        fileobj = io.BytesIO(bytes(self.src_content, 'utf8'))
        fileobj.name = 'main.md'
        fileobj.seek(0)
        self.codebase_release.add_doc_upload(fileobj)

        with open(str(self.codebase_release.get_library_path('docs', 'main.md'))) as f:
            self.assertEqual(f.read(), self.src_content)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.LIBRARY_ROOT, ignore_errors=True)
