import json
import logging
import mimetypes
import os
import re
import shutil
import tarfile
import zipfile
from enum import Enum
from functools import total_ordering
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import bagit
import rarfile
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import File
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from core import fs

logger = logging.getLogger(__name__)


class FsLogError(Exception): pass


class StagingDirectories(Enum):
    # Directory containing original files uploaded (such as zip files)
    originals = 1
    # Directory containing submission information package files
    sip = 2
    # Directory containing archive information package files
    aip = 3


class FileCategoryDirectories(Enum):
    code = 1
    data = 2
    docs = 3
    media = 4
    originals = 5
    results = 6


@total_ordering
class MessageLevels(Enum):
    info = 0
    warning = 1
    error = 2
    critical = 3

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


mimetypes.add_type('text/x-rst', '.rst')
mimetypes.add_type('text/x-netlogo', '.nls')
mimetypes.add_type('text/x-netlogo', '.nlogo')
mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('text/x-r-source', '.r')

MIMETYPE_MATCHER = {
    FileCategoryDirectories.code: re.compile(r'.*'),
    FileCategoryDirectories.data: re.compile(r'.*'),
    FileCategoryDirectories.docs: re.compile(r'text/markdown|application/pdf|text/plain|text/x-rtf'),
    FileCategoryDirectories.media: re.compile(r'image/.*|video/.*'),
    FileCategoryDirectories.originals: re.compile(r'.*'),
    FileCategoryDirectories.results: re.compile(r'.*')
}


def get_category(name) -> FileCategoryDirectories:
    category_name = Path(name).parts[0]
    try:
        return FileCategoryDirectories[category_name]
    except KeyError:
        raise ValidationError('Target folder name {} invalid. Must be one of {}'.format(category_name, list(
            d.name for d in FileCategoryDirectories)))


def get_mimetype_matcher(name):
    category = get_category(name)
    return MIMETYPE_MATCHER[category]


def files_in_dir(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            relpath = os.path.join(dirpath, filename)
            fullpath = os.path.join(path, relpath)
            if os.path.isfile(fullpath):
                yield relpath


class MessageGroup:
    def __init__(self):
        self.msgs = []
        self.level = MessageLevels.info

    def __bool__(self):
        return len(self.msgs) > 0

    def __repr__(self):
        return '<MessageGroup {0}>'.format(repr(self.msgs))

    def append(self, msg: Optional):
        if msg is not None and msg:
            if isinstance(msg, MessageGroup):
                self.msgs += msg.msgs
            else:
                self.msgs.append(msg)
            self.level = max(self.level, msg.level)

    def serialize(self):
        """Return a list of message along with message level"""
        logs = []
        for msg in self.msgs:
            logs.append(msg.serialize())
        return logs, self.level


class Message:
    level = MessageLevels.critical

    def __init__(self, msg, level: MessageLevels = MessageLevels.info):
        self.level = level
        self.msg = msg

    def __repr__(self):
        return repr(self.serialize())

    def serialize(self):
        return {'level': self.level.name, 'msg': self.msg}


def create_fs_message(detail, stage: StagingDirectories, level: MessageLevels):
    return Message({'detail': str(detail), 'stage': stage.name}, level=level)


class CodebaseReleaseStorage(FileSystemStorage):
    stage = None

    def __init__(self, raise_exception_level, location=None, base_url=None, file_permissions_mode=None,
                 directory_permissions_mode=None):
        super().__init__(location=location, base_url=base_url,
                         file_permissions_mode=file_permissions_mode,
                         directory_permissions_mode=directory_permissions_mode)
        self._raise_exception_level = raise_exception_level

    def validate_file(self, name, content) -> Optional:
        msgs = MessageGroup()
        if fs.has_system_files(name):
            msgs.append(self.warning("'{}' has a mac os x system directory".format(name)))
        if fs.is_system_file(name):
            msgs.append(self.warning("'{}' is a system file".format(name)))
        return msgs

    def validate(self):
        """Construct an audit report of a releases files"""
        msgs = MessageGroup()
        for filename in self.list():
            with self.open(filename) as content:
                msgs.append(self.validate_file(filename, content))
        return msgs

    def list(self, category: Optional[FileCategoryDirectories] = None, absolute=False):
        path = Path(self.location)
        if category is not None:
            path = path.joinpath(category.name)
        for p in path.rglob('*'):
            if p.is_file():
                if absolute:
                    yield p
                else:
                    yield p.relative_to(path)

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            raise ValueError(
                'Storage filename "%s" already taken' % name
            )
        return name

    def create_msg(self):
        return MessageGroup()

    def info(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.info)

    def warning(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.warning)

    def error(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.error)

    def critical(self, msg):
        return create_fs_message(msg, self.stage, MessageLevels.critical)

    def log_save(self, name, content):
        if name is None:
            name = content.name
        msgs = self.validate_file(name, content)
        if msgs.level >= self._raise_exception_level:
            return msgs

        try:
            self.save(name, content)
        except IOError as e:
            msgs.append(self.error(e))
        except ValueError as e:
            msgs.append(self.error(e))
        return msgs

    def clear_category(self, category: FileCategoryDirectories):
        shutil.rmtree(os.path.join(self.location, category.name), ignore_errors=True)

    def clear(self):
        shutil.rmtree(self.location, ignore_errors=True)

    def log_delete(self, name):
        try:
            self.delete(name)
        except IOError as e:
            return self.error(e)
        return None


class CodebaseReleaseOriginalStorage(CodebaseReleaseStorage):
    stage = StagingDirectories.originals

    def validate_mimetype(self, name):
        mimetype_matcher = get_mimetype_matcher(name)
        mimetype = mimetypes.guess_type(name)[0]
        if mimetype is None or not mimetype_matcher.match(mimetype):
            return self.warning('File type mismatch for file {}'.format(name))
        return None

    def get_existing_archive_name(self, category: FileCategoryDirectories):
        for p in self.list(category):
            if p.is_file() and fs.is_archive(p):
                return str(p)
        return None

    def is_archive_directory(self, category):
        for p in self.list(category, absolute=True):
            if p.is_file() and fs.is_archive(str(p)):
                return True
        return False

    def has_existing_archive(self, category):
        path = Path(self.location, category.name)
        os.makedirs(str(path), exist_ok=True)
        for subpath in path.glob('*'):
            if subpath.is_file() and fs.is_archive(str(subpath)):
                return True
        return False

    def validate_file(self, name, content):
        msgs = super().validate_file(name, content)
        if msgs.level >= self._raise_exception_level:
            return msgs
        category = get_category(name)
        if self.has_existing_archive(category):
            msgs.append(
                self.error('File cannot be added to directory with archive in it. Please clear category and try again.'))
            return msgs
        if os.listdir(os.path.join(self.location, category.name)) and fs.is_archive(name):
            msgs.append(self.error('Archive cannot be added to a directory that already has files in it. '
                                   'Please clear category and try again'))
            return msgs

        msgs.append(self.validate_mimetype(name))
        return msgs


class CodebaseReleaseSipStorage(CodebaseReleaseStorage):
    """Places files from the uploaded folder into the sip (submission information package)

    Archives from the uploads folder get expanded when placed in the sip folder"""

    stage = StagingDirectories.sip

    def validate_mimetype(self, name):
        get_category(name)
        mimetype_matcher = get_mimetype_matcher(name)
        mimetype = mimetypes.guess_type(name)[0]
        if mimetype is None or not mimetype_matcher.match(mimetype):
            return self.warning('File type mismatch for file {}'.format(name))
        return None

    def validate_file(self, name, content):
        msgs = super().validate_file(name, content)
        if msgs.level >= self._raise_exception_level:
            return msgs
        msgs.append(self.validate_mimetype(name))
        return msgs

    def make_bag(self, metadata):
        return fs.make_bag(self.location, metadata)


class CodebaseReleaseAipStorage(CodebaseReleaseStorage):
    """Places files from the sip folder into aip"""

    def import_sip(self, sip_storage: CodebaseReleaseSipStorage):
        shutil.copytree(sip_storage.location, self.location)


class CodebaseReleaseFsApi:

    """
    Interface to maintain files associated with a codebase

    This is not currently protected against concurrent file access. However, since only
    the submitter can edit files associated with a codebase release there is little
    """

    DEFAULT_CODEMETA_DATA = {
        "@context": ["https://doi.org/doi:10.5063/schema/codemeta-2.0", "http://schema.org"],
        "@type": "SoftwareSourceCode",
        "provider": {
            "@id": "https://www.comses.net",
            "@type": "Organization",
            "name": "CoMSES Network (CoMSES)",
            "url": "https://www.comses.net"
        },
    }

    def __init__(self, uuid, identifier, version_number, raise_exception_level):
        self.uuid = uuid
        self.identifier = identifier
        self.version_number = version_number
        self._raise_exception_level = raise_exception_level

    def logfilename(self):
        return self.rootdir.joinpath('audit.log')

    @property
    def lockfilename(self):
        return self.rootdir.joinpath('lock')

    @property
    def archivepath(self):
        return self.rootdir.joinpath('archive.zip')

    @property
    def rootdir(self):
        return Path(settings.LIBRARY_ROOT, str(self.uuid),
                    'releases', 'v{}'.format(self.version_number)).absolute()

    @property
    def aip_dir(self):
        return self.rootdir.joinpath('aip')

    @property
    def aip_contents_dir(self):
        return self.aip_dir.joinpath('data')

    @property
    def originals_dir(self):
        return self.rootdir.joinpath('originals')

    @property
    def sip_dir(self):
        return self.rootdir.joinpath('sip')

    @property
    def sip_contents_dir(self):
        return self.sip_dir.joinpath('data')

    def get_originals_storage(self, originals_dir=None):
        if originals_dir is None:
            originals_dir = self.originals_dir
        return CodebaseReleaseOriginalStorage(raise_exception_level=self._raise_exception_level,
                                              location=str(originals_dir))

    def get_sip_storage(self):
        return CodebaseReleaseSipStorage(raise_exception_level=self._raise_exception_level,
                                         location=str(self.sip_contents_dir))

    def get_aip_storage(self):
        return CodebaseReleaseAipStorage(raise_exception_level=self._raise_exception_level,
                                         location=str(self.aip_contents_dir))

    def get_stage_storage(self, stage: StagingDirectories):
        if stage == StagingDirectories.originals:
            return self.get_originals_storage()
        elif stage == StagingDirectories.sip:
            return self.get_sip_storage()
        elif stage == StagingDirectories.aip:
            return self.get_aip_storage()
        else:
            raise ValueError('StageDirectories values {} not valid'.format(stage))

    def get_sip_list_url(self, category: FileCategoryDirectories):
        return reverse('library:codebaserelease-sip-files-list',
                       kwargs={'identifier': str(self.identifier), 'version_number': self.version_number,
                               'category': category.name})

    def get_originals_list_url(self, category: FileCategoryDirectories):
        return reverse('library:codebaserelease-original-files-list',
                       kwargs={'identifier': str(self.identifier), 'version_number': self.version_number,
                               'category': category.name})

    def get_absolute_url(self, category: FileCategoryDirectories, relpath: Path):
        return reverse('library:codebaserelease-original-files-detail',
                       kwargs={'identifier': str(self.identifier), 'version_number': self.version_number,
                               'category': category.name, 'relpath': str(relpath)})

    def _create_msg_group(self):
        return MessageGroup()

    def initialize(self):
        sip_dir = self.sip_dir
        os.makedirs(str(sip_dir), exist_ok=True)
        # touch a codemeta.json file in the sip_dir so make_bag has something to
        self.initialize_codemeta(sip_dir.joinpath('codemeta.json'))
        fs.make_bag(str(sip_dir), {})

    def initialize_codemeta(self, path=None):
        """
        Returns True if a fresh codemeta.json file was created, False otherwise
        :param path: an optional path to the codemeta file. If no path is passed in, it tries to create a new
        codemeta.json file in the sip_dir bound to the CodebaseRelease associated with this FS API
        :return:
        """
        if path is None:
            path = self.sip_dir.joinpath('codemeta.json')
        if path.exists():
            return False
        with path.open('w') as codemeta_out:
            json.dump(self.DEFAULT_CODEMETA_DATA, codemeta_out)
        return True

    def retrieve_archive(self):
        return (File(self.archivepath.open('rb')), 'application/zip')

    def clear_category(self, category: FileCategoryDirectories):
        originals_storage = self.get_originals_storage()
        originals_storage.clear_category(category)
        sip_storage = self.get_sip_storage()
        sip_storage.clear_category(category)

    def list(self, stage: StagingDirectories, category: Optional[FileCategoryDirectories]):
        stage_storage = self.get_stage_storage(stage)
        return [str(p) for p in stage_storage.list(category)]

    def retrieve(self, stage: StagingDirectories, category: FileCategoryDirectories, relpath: Path):
        stage_storage = self.get_stage_storage(stage)
        relpath = Path(category.name, relpath)
        return stage_storage.open(str(relpath))

    def delete(self, category: FileCategoryDirectories, relpath: Path):
        originals_storage = self.get_originals_storage()
        sip_storage = self.get_sip_storage()
        relpath = Path(category.name, relpath)
        logs = MessageGroup()
        if originals_storage.is_archive_directory(category):
            self.clear_category(category)
        else:
            if not originals_storage.exists(str(relpath)):
                logs.append(create_fs_message('No file at path {} to delete'.format(str(relpath)),
                                              StagingDirectories.originals, MessageLevels.error))
                return logs
            logs.append(sip_storage.log_delete(str(relpath)))
            logs.append(originals_storage.log_delete(str(relpath)))
        return logs

    def _add_to_sip(self, name, content, category: FileCategoryDirectories, sip_storage):
        filename = self.originals_dir.joinpath(name)
        if fs.is_archive(name):
            archive_extractor = ArchiveExtractor(sip_storage)
            return archive_extractor.process(category=category, filename=str(filename))
        else:
            return sip_storage.log_save(name=name, content=content)

    def add_category(self, category: FileCategoryDirectories, src):
        logger.info("adding category {}".format(category.name))
        originals_storage = self.get_originals_storage()
        msgs = self._create_msg_group()
        for dirpath, dirnames, filenames in os.walk(src):
            for filename in filenames:
                filename = os.path.join(dirpath, filename)
                name = os.path.join(category.name, str(Path(filename).relative_to(src)))
                logger.debug("adding file {}".format(name))
                with open(filename, 'rb') as content:
                    msgs.append(originals_storage.log_save(name, content))
        return msgs

    def add(self, category: FileCategoryDirectories, content, name=None):
        if name is None:
            name = os.path.join(category.name, content.name)
        else:
            name = os.path.join(category.name, name)

        originals_storage = self.get_originals_storage()
        sip_storage = self.get_sip_storage()

        msgs = originals_storage.log_save(name, content)
        if msgs.level >= self._raise_exception_level:
            return msgs
        msgs.append(self._add_to_sip(name=name, content=content, category=category, sip_storage=sip_storage))

        return msgs

    def get_or_create_sip_bag(self, bagit_info):
        logger.info("creating bagit metadata")
        bag = bagit.Bag(str(self.sip_dir))
        for k, v in bagit_info.items():
            bag.info[k] = v
        return bag.save(manifests=True)

    def build_sip(self, originals_dir: Optional[str] = None):
        logger.info("building sip")
        if originals_dir is None:
            originals_dir = self.originals_dir
        originals_storage = self.get_originals_storage(originals_dir)
        sip_storage = self.get_sip_storage()
        sip_storage.clear()

        msgs = self._create_msg_group()
        for name in originals_storage.list():
            path = self.originals_dir.joinpath(name)
            logger.debug("adding file: {}".format(path.relative_to(self.originals_dir)))
            category = get_category(Path(name).parts[0])
            with File(path.open('rb')) as f:
                msgs.append(self._add_to_sip(name=str(name), content=f, category=category, sip_storage=sip_storage))

        return msgs

    def build_aip(self, sip_dir: Optional[str] = None):
        logger.info("building aip")
        if sip_dir is None:
            sip_dir = str(self.sip_dir)
        shutil.rmtree(str(self.aip_dir), ignore_errors=True)
        shutil.copytree(sip_dir, str(self.aip_dir))

    def build_archive(self):
        if not self.archivepath.exists():
            logger.info("building archive")
            if self.aip_contents_dir.exists():
                with zipfile.ZipFile(str(self.archivepath), 'w') as archive:
                    for root_path, dirs, file_paths in os.walk(str(self.aip_contents_dir)):
                        for file_path in file_paths:
                            path = Path(root_path, file_path)
                            archive.write(str(path), arcname=str(path.relative_to(self.aip_contents_dir)))
                logger.info("building archive succeeded")
            else:
                logger.error("building archive failed - no aip directory")


class ArchiveExtractor:
    def __init__(self, sip_storage: CodebaseReleaseSipStorage):
        self.sip_storage = sip_storage

    def extractall(self, unpack_destination, filename):
        mimetype = mimetypes.guess_type(filename)[0]
        if mimetype == 'application/zip':
            with zipfile.ZipFile(filename, 'r') as z:
                z.extractall(path=unpack_destination)

        elif mimetype == 'application/x-tar':
            with tarfile.TarFile(filename, 'r') as t:
                t.extractall(path=unpack_destination)

        elif mimetype == 'application/rar':
            if hasattr(filename, 'name'):
                raise TypeError('RAR archives cannot be extracted from file objects. Requires string filename')

            with rarfile.RarFile(filename, 'r') as r:
                r.extractall(path=unpack_destination)

        else:
            return Message('Archive {} is unsupported'.format(filename))

    def find_root_directory(self, basedir):
        for dirpath, dirnames, filenames in os.walk(basedir):
            if len(dirnames) != 1 or len(filenames) != 0:
                return dirpath

    def process(self, category: FileCategoryDirectories, filename: str):
        msgs = MessageGroup()
        try:
            with TemporaryDirectory() as d:
                try:
                    msg = self.extractall(unpack_destination=d, filename=filename)
                except zipfile.BadZipFile as e:
                    msg = create_fs_message(e, StagingDirectories.sip, MessageLevels.error)
                except tarfile.TarError as e:
                    msg = create_fs_message(e, StagingDirectories.sip, MessageLevels.error)
                except Exception as e:
                    logger.exception("Error unpacking archive")
                    msg = create_fs_message(e, StagingDirectories.sip, MessageLevels.error)

                if msg is not None:
                    return msg
                rootdir = self.find_root_directory(d)
                for unpacked_file in Path(rootdir).rglob('*'):
                    if unpacked_file.is_file():
                        with File(unpacked_file.open('rb')) as unpacked_fileobj:
                            relpath = Path(category.name, unpacked_file.relative_to(rootdir))
                            msgs.append(self.sip_storage.log_save(name=str(relpath), content=unpacked_fileobj))
        except FsLogError as e:
            msgs.append(e.args[0])
        return msgs
