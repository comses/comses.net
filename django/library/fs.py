import mimetypes
import tarfile
import zipfile
from enum import Enum
from pathlib import Path

import io
import os

import shutil

import rarfile
import re
import structlog
from tempfile import TemporaryDirectory
from typing import List, Union

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from core import fs
from library.models import CodebaseRelease


class FsError(Exception): pass


class FsFileOrDirectoryNotFound(FsError): pass


class FsFileOverwrite(FsError): pass


class PossibleDirectories(Enum):
    code = 1
    data = 2
    docs = 3
    media = 4
    originals = 5
    results = 6


mimetypes.add_type('text/x-rst', '.rst')
mimetypes.add_type('text/x-netlogo', '.nls')
mimetypes.add_type('text/x-netlogo', '.nlogo')
mimetypes.add_type('text/markdown', '.md')


class ListLogger:
    """Saves events to a list"""

    def __init__(self):
        self.events = []

    @classmethod
    def create_bound_list_logger(cls, processors=None):
        if processors is None:
            processors = [
                structlog.processors.TimeStamper(fmt='iso'),
                structlog.stdlib.add_log_level,
            ]
        return structlog.wrap_logger(cls(), processors=processors)

    def msg(self, *args, **kwargs):
        self.events.append((args, kwargs))

    log = debug = info = warn = warning = msg
    failure = err = error = critical = exception = msg


class ActivityLogger:
    def __init__(self, print_logger, list_logger):
        self.print_logger = print_logger
        self.list_logger = list_logger

    @classmethod
    def from_fileobj(cls, fileobj):
        print_logger = structlog.wrap_logger(structlog.PrintLogger(fileobj), processors=[
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(sort_keys=True)
        ])
        return cls(print_logger=print_logger, list_logger=ListLogger.create_bound_list_logger())

    def bind(self, **new_values):
        list_logger = self.list_logger.bind(**new_values)
        print_logger = self.print_logger.bind(**new_values)
        return self.__class__(print_logger=print_logger, list_logger=list_logger)

    def unbind(self, *keys):
        list_logger = self.list_logger.unbind(*keys)
        print_logger = self.print_logger.unbind(*keys)
        return self.__class__(print_logger=print_logger, list_logger=list_logger)

    def new(self, **new_values):
        list_logger = self.list_logger.new(**new_values)
        print_logger = self.print_logger.new(**new_values)
        return self.__class__(print_logger=print_logger, list_logger=list_logger)

    def getvalue(self):
        return self.list_logger.getvalue()

    def msg(self, *args, **kwargs):
        self.list_logger.msg(*args, **kwargs)
        self.print_logger.msg(*args, **kwargs)

    log = debug = info = warn = warning = msg
    failure = err = error = critical = exception = msg


class CodebaseReleaseFsApi:
    def __init__(self, codebase_release: CodebaseRelease, logger=None):
        self.codebase_release = codebase_release
        self.identifier = codebase_release.codebase.identifier
        self.version_number = codebase_release.version_number
        self.sip_rootdir = codebase_release.library_path.joinpath('sip').absolute()
        self.aipdir = codebase_release.library_path.joinpath('aip').absolute()
        self.logger = logger

    @staticmethod
    def logfilename(codebase_release: CodebaseRelease):
        return codebase_release.library_path.joinpath('audit.log')

    @property
    def rootdir(self):
        return self.codebase_release.codebase.subpath(
            'releases', 'v{}'.format(self.codebase_release.version_number)).absolute()

    @property
    def aip_contents_dir(self):
        return self.rootdir.join('aip', 'data')

    @property
    def sip_originals_dir(self):
        return self.rootdir.joinpath('sip', 'originals')

    @property
    def sip_contents_dir(self):
        return self.rootdir.joinpath('sip', 'data')

    def bind(self, **new_values):
        logger = self.logger.bind(**new_values)
        return self.__class__(self.codebase_release, logger)

    MIMETYPE_MATCHER = {
        # Remove code / data /originals
        PossibleDirectories.code: re.compile(r'text/.*|application/json'),
        PossibleDirectories.data: re.compile(r'text/.*'),
        PossibleDirectories.docs: re.compile(r'text/markdown|application/pdf|text/plain|text/x-rtf'),
        PossibleDirectories.media: re.compile(r'image/.*|video/.*'),
        PossibleDirectories.originals: re.compile(r'text/.*|image/.*|video/.*'),
    }

    def mimetype_matcher(self, dest_folder: PossibleDirectories):
        return self.MIMETYPE_MATCHER[dest_folder]

    def get_absolute_url(self, folder: PossibleDirectories, relpath: Path):
        return reverse('library:codebaserelease-unpublished-files-detail',
                       kwargs={'identifier': self.identifier, 'version_number': self.version_number,
                               'foldername': folder.name, 'relpath': str(relpath)})

    def get_list_url(self, folder: PossibleDirectories):
        return reverse('library:codebaserelease-unpublished-files-list',
                       kwargs={'identifier': self.identifier, 'version_number': self.version_number,
                               'foldername': folder.name})

    def get_paths(self, folder: PossibleDirectories, relpath: Path):
        basepath = self.sip_contents_dir.joinpath(folder.name)
        # Python 3.5 does not support resolving paths that do not (completely) exist on the fs.
        # When we upgrade 3.6 we could use basepath.joinpath(relpath).resolve(strict=False)
        path = Path(os.path.realpath(str(basepath.joinpath(relpath))))
        fs.is_subpath(basepath, path)
        return basepath, path

    def is_correct_mimetype(self, path: Path, dest_folder: PossibleDirectories):
        mimetype = mimetypes.guess_type(str(path))[0] or ''
        mimetype_matcher = self.mimetype_matcher(dest_folder=dest_folder)
        if not mimetype_matcher.match(mimetype):
            self.logger.error('Wrong mimetype', filename=str(path), mimetype=mimetype)
            return False
        return True

    def list(self, folder: PossibleDirectories):
        """List contents of """
        for path in self.sip_contents_dir.joinpath(folder.name).rglob('*'):
            relpath = path.relative_to(self.sip_contents_dir)
            yield dict(path=str(relpath), url=self.get_absolute_url(folder, relpath))

    def retrieve(self, folder: PossibleDirectories, relpath: Path):
        path = self.sip_rootdir.joinpath(folder, relpath).resolve()
        assert path in self.sip_rootdir

        if path.is_file():
            return path.open('rb')
        else:
            p = Path(folder.name).joinpath(relpath)
            raise serializers.ValidationError('File "{}" does not exist'.format(str(p)))

    def delete(self, folder: PossibleDirectories, relpath: Path):
        assert self.logger is not None
        basepath, path = self.get_paths(folder, relpath)

        p = str(path.relative_to(basepath))
        if path.is_file():
            self.logger.info('Deleting file', filename=p)
            os.unlink(str(path))
        elif path.is_dir():
            self.logger.info('Deleting folder', filename=p)
            shutil.rmtree(str(path))
        else:
            raise serializers.ValidationError('File or directory "{}" does not exist'.format(p))

    def has(self, folder: PossibleDirectories, path: Path):
        return self.sip_rootdir.joinpath(folder.name, path).exists()

    def add(self, fileobj, dest_folder: PossibleDirectories):
        assert self.logger is not None
        relpath = Path(fileobj.name)
        basepath, dest_originals = self.get_paths(PossibleDirectories.originals,
                                                  Path(dest_folder.name).joinpath(relpath))
        if fs.is_archive(str(dest_originals)):
            with dest_originals.open('wb') as f:
                self.logger.info('Adding archive', filename=str(dest_originals.relative_to(self.sip_contents_dir)))
                f.write(fileobj)
            archive_extractor = ArchiveExtractor(self, dest_folder)
            archive_extractor.process(str(dest_originals))
        else:
            if self.is_correct_mimetype(dest_folder=dest_folder, path=relpath):
                os.makedirs(str(dest_originals.parent), exist_ok=True)
                if dest_originals.exists():
                    self.logger.warn('Overwriting file', filename=str(relpath))
                with dest_originals.open('wb') as f:
                    self.logger.info('Adding file', filename=str(dest_originals.relative_to(self.sip_contents_dir)))
                    f.write(fileobj.read())
                self.copy(dest_originals, dest_folder)

    def move(self, src: Path, dest_folder: PossibleDirectories):
        assert self.logger is not None
        if self.is_correct_mimetype(src, dest_folder):
            dest = self.sip_contents_dir.joinpath(dest_folder.name, src.name)
            os.makedirs(str(dest.parent), exist_ok=True)
            self.logger.info('Moving file', original_filename=str(src),
                             filename=str(dest.relative_to(self.sip_contents_dir)))
            shutil.move(str(src), str(dest))
            return dest
        return None

    def copy(self, src: Path, dest_folder: PossibleDirectories):
        """Copy a file from the originals folder to the destination folder"""
        dest = self.sip_contents_dir.joinpath(dest_folder.name, src.name)
        self.logger.info('Copying file', original_filename=str(src.relative_to(self.sip_contents_dir)),
                         filename=str(dest.relative_to(self.sip_contents_dir)))
        os.makedirs(str(dest.parent), exist_ok=True)
        shutil.copy(str(src), str(dest))
        return dest


class CodebaseReleaseFsApiWithActivityLog:
    """File API for a codebase release with an activity log for logging

    This class is for creating the codebase release api without having to manually open and close the log file"""

    def __init__(self, codebase_release):
        self.codebase_release = codebase_release

    def __enter__(self):
        logfile_path = CodebaseReleaseFsApi.logfilename(self.codebase_release)
        os.makedirs(str(logfile_path.parent), exist_ok=True)
        self.logfile = logfile_path.open('a')
        logger = ActivityLogger.from_fileobj(self.logfile)
        self.codebase_release_fs_api = CodebaseReleaseFsApi(self.codebase_release, logger=logger)
        return self.codebase_release_fs_api

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logfile.close()


class ArchiveExtractor:
    def __init__(self, codebase_release_fs_api: CodebaseReleaseFsApi, dest_folder: PossibleDirectories):
        self.codebase_release_fs_api = codebase_release_fs_api
        self.dest_folder = dest_folder

    @classmethod
    def from_codebase_release(cls, codebase_release: CodebaseRelease, dest_folder: PossibleDirectories, logger):
        codebase_release_fs_api = CodebaseReleaseFsApi(codebase_release, logger)
        return cls(codebase_release_fs_api=codebase_release_fs_api, dest_folder=dest_folder)

    def archivename(self, fileobj):
        return self.codebase_release_fs_api.sip_rootdir.joinpath(PossibleDirectories.originals.name, fileobj.name)

    def get_filename(self, filename_or_fileobj):
        if hasattr(filename_or_fileobj, 'name'):
            return filename_or_fileobj.name
        elif isinstance(filename_or_fileobj, str):
            return str(filename_or_fileobj)
        else:
            raise TypeError(filename_or_fileobj)

    def add(self, fileobj, log):
        log.debug('Adding archive to originals folder')
        with open(str(self.archivename(fileobj)), 'w') as f:
            fileobj.write(f)
        log.info('Added archive to originals folder')

    def extractall(self, path, filename_or_fileobj):
        filename = self.get_filename(filename_or_fileobj)
        mimetype = mimetypes.guess_type(filename)[0]
        if mimetype == 'application/zip':
            with zipfile.ZipFile(filename_or_fileobj, 'r') as z:
                z.extractall(path=path)

        elif mimetype == 'application/x-tar':
            with tarfile.TarFile(filename_or_fileobj, 'r') as t:
                t.extractall(path=path)

        elif mimetype == 'application/rar':
            if hasattr(filename_or_fileobj, 'name'):
                raise TypeError('RAR archives cannot be extracted from file objects. Requires string filename')

            with rarfile.RarFile(filename_or_fileobj, 'r') as r:
                r.extractall(path=path)

        else:
            raise ValueError('Archive {} is unsupported'.format(filename))

    def process(self, filename_or_fileobj: Union[str, io.TextIOWrapper, io.BytesIO]):
        api = self.codebase_release_fs_api.bind(archive_filename=self.get_filename(filename_or_fileobj))
        api.logger.debug('Extracting archive')
        with TemporaryDirectory() as d:
            self.extractall(path=d, filename_or_fileobj=filename_or_fileobj)
            for file_path in Path(d).rglob('*'):
                if file_path.is_file():
                    self.codebase_release_fs_api.move(file_path, self.dest_folder)
        api.logger.info('Extracted archive')
