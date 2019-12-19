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

import rarfile
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import File
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from core import fs

logger = logging.getLogger(__name__)


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
    debug = 0
    info = 1
    warning = 2
    error = 3
    critical = 4

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def downgrade(self, minimum=0):
        return MessageLevels(max(self.value - 1, minimum))


mimetypes.add_type('text/x-rst', '.rst')
mimetypes.add_type('text/x-netlogo', '.nls')
mimetypes.add_type('text/x-netlogo', '.nlogo')
mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('text/x-r-source', '.r')

ACCEPT_ALL_REGEX = re.compile(r'.*')

MIMETYPE_MATCHER = {
    FileCategoryDirectories.code: ACCEPT_ALL_REGEX,
    FileCategoryDirectories.data: ACCEPT_ALL_REGEX,
    FileCategoryDirectories.docs: re.compile(r'text/markdown|application/pdf|text/plain|text/x-rtf|application/vnd.oasis.opendocument.text'),
    FileCategoryDirectories.media: re.compile(r'image/.*|video/.*'),
    FileCategoryDirectories.originals: ACCEPT_ALL_REGEX,
    FileCategoryDirectories.results: ACCEPT_ALL_REGEX
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
    def __init__(self, msgs=None):
        self.msgs = []
        self.level = MessageLevels.debug

        if msgs is not None:
            for msg in msgs:
                self.append(msg)

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

    def downgrade(self):
        self.level = self.level.downgrade()
        for msg in self.msgs:
            msg.level = msg.level.downgrade()

    @property
    def has_errors(self):
        return self.level >= MessageLevels.error

    def serialize(self):
        """Return a list of message along with message level"""
        logs = []
        for msg in self.msgs:
            logs.append(msg.serialize())
        return logs, self.level


class Message:
    def __init__(self, msg, level: MessageLevels = MessageLevels.info):
        self.level = level
        self.msg = msg

    def __repr__(self):
        return repr(self.serialize())

    def serialize(self):
        return {'level': self.level.name, 'msg': self.msg}

    @property
    def has_errors(self):
        return self.level >= MessageLevels.error


def create_fs_message(detail, stage: StagingDirectories, level: MessageLevels):
    return Message({'detail': str(detail), 'stage': stage.name}, level=level)


class CodebaseReleaseStorage(FileSystemStorage):
    stage = None

    def __init__(self, mimetype_mismatch_message_level,
                 location=None, base_url=None, file_permissions_mode=None,
                 directory_permissions_mode=None):
        super().__init__(location=location, base_url=base_url,
                         file_permissions_mode=file_permissions_mode,
                         directory_permissions_mode=directory_permissions_mode)
        self.mimetype_mismatch_message_level = mimetype_mismatch_message_level

    def validate_system_file(self, name, content) -> Optional[Message]:
        # FIXME: do we expect validate_file being run on full paths?
        if fs.has_system_files(name):
            return self.error("Ignored system file '{}'".format(name))
        return None

    def validate_mimetype(self, name):
        mimetype_matcher = get_mimetype_matcher(name)
        mimetype = mimetypes.guess_type(name)[0]
        mimetype = mimetype if mimetype else '*/*'
        if not mimetype_matcher.match(mimetype):
            return create_fs_message("Ignored file '{}'. File type mismatch.".format(name), self.stage,
                                     self.mimetype_mismatch_message_level)
        return None

    def validate_file(self, name, content):
        msgs = MessageGroup()
        msgs.append(self.validate_system_file(name, content))
        msgs.append(self.validate_mimetype(name))
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
        if msgs.has_errors:
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
        for p in Path(self.location).iterdir():
            if p.is_dir():
                shutil.rmtree(str(p), ignore_errors=True)

    def log_delete(self, name):
        try:
            self.delete(name)
        except IOError as e:
            return self.error(e)
        return None


class CodebaseReleaseOriginalStorage(CodebaseReleaseStorage):
    stage = StagingDirectories.originals

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
        category = get_category(name)
        if self.has_existing_archive(category):
            msgs.append(self.error(
                'File cannot be added to directory with archive in it. Please clear category and try again.'))
        if os.listdir(os.path.join(self.location, category.name)) and fs.is_archive(name):
            msgs.append([self.error('Archive cannot be added to a directory that already has files in it. '
                                    'Please clear category and try again')])
        return msgs


class CodebaseReleaseSipStorage(CodebaseReleaseStorage):
    """Places files from the uploaded folder into the sip (submission information package)

    Archives from the uploads folder get expanded when placed in the sip folder"""

    stage = StagingDirectories.sip

    def make_bag(self, metadata):
        return fs.make_bag(self.location, metadata)


class CodebaseReleaseAipStorage(CodebaseReleaseStorage):
    """Places files from the sip folder into aip"""

    def import_sip(self, sip_storage: CodebaseReleaseSipStorage):
        shutil.copytree(sip_storage.location, self.location)


class CodebaseReleaseFsApi:
    """
    Interface to maintain files associated with a codebase

    FIXME: This is not currently protected against concurrent file access but only the submitter can edit files
    associated with a codebase release at the moment, implement file locks if this assumption turns out badly
    """

    def __init__(self, uuid, identifier, version_number, release_id,
                 system_file_presence_message_level=MessageLevels.error,
                 mimetype_mismatch_message_level=MessageLevels.error,
                 codemeta=None):
        self.uuid = uuid
        self.identifier = identifier
        self.version_number = version_number
        self.release_id = release_id
        self.mimetype_mismatch_message_level = mimetype_mismatch_message_level
        self.codemeta = codemeta

    def logfilename(self):
        return self.rootdir.joinpath('audit.log')

    @property
    def lockfilename(self):
        return self.rootdir.joinpath('lock')

    @property
    def archivepath(self):
        return self.rootdir.joinpath('archive.zip')

    @property
    def review_archivepath(self):
        return self.rootdir.joinpath('review_archive.zip')

    @property
    def rootdir(self):
        return Path(settings.LIBRARY_ROOT, str(self.uuid), 'releases', str(self.release_id)).absolute()

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
    def codemeta_path(self):
        return self.sip_dir.joinpath('codemeta.json')

    @property
    def sip_contents_dir(self):
        return self.sip_dir.joinpath('data')

    def get_originals_storage(self, originals_dir=None):
        if originals_dir is None:
            originals_dir = self.originals_dir
        return CodebaseReleaseOriginalStorage(
            mimetype_mismatch_message_level=self.mimetype_mismatch_message_level,
            location=str(originals_dir)
        )

    def get_sip_storage(self, mimetype_mismatch_message_level=None):
        if mimetype_mismatch_message_level is None:
            mimetype_mismatch_message_level = self.mimetype_mismatch_message_level
        return CodebaseReleaseSipStorage(mimetype_mismatch_message_level=mimetype_mismatch_message_level,
                                         location=str(self.sip_contents_dir))

    def get_aip_storage(self):
        return CodebaseReleaseAipStorage(mimetype_mismatch_message_level=self.mimetype_mismatch_message_level,
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
        if not sip_dir.exists():
            os.makedirs(sip_dir, exist_ok=True)
            fs.make_bag(str(sip_dir), {})

    def create_or_update_codemeta(self, force=False):
        """
        Returns True if a codemeta.json file was created, False otherwise
        :param metadata: an optional dictionary with codemeta properties
        :return:
        """
        path = self.codemeta_path
        if force or not path.exists():
            with path.open(mode='w', encoding='utf-8') as codemeta_out:
                json.dump(self.codemeta.to_dict(), codemeta_out)
            return True
        return False

    def get_codemeta_json(self):
        return self.codemeta.to_json()

    def build_published_archive(self, bagit_info, force=True):
        self.get_or_create_sip_bag(bagit_info)
        self.build_aip()
        self.build_archive(force=force)

    def build_review_archive(self):
        self.create_or_update_codemeta(force=True)
        shutil.make_archive(str(self.review_archivepath.with_suffix('')),
                            format='zip', root_dir=str(self.sip_contents_dir))
        return self.review_archivepath

    @property
    def codemeta_uri(self):
        return self.codemeta_path.relative_to(settings.LIBRARY_ROOT)

    @property
    def archive_uri(self):
        """ returns the internal URI used by nginx to access this release's official archive package """
        return self.archivepath.relative_to(settings.LIBRARY_ROOT)

    @property
    def review_archive_uri(self):
        """ returns the internal uri used by nginx to access this release's review archive package """
        return self.review_archivepath.relative_to(settings.LIBRARY_ROOT)

    @property
    def archive_size(self):
        return self.archivepath.stat().st_size

    @property
    def review_archive_size(self):
        return self.review_archivepath.stat().st_size

    def clear_category(self, category: FileCategoryDirectories):
        originals_storage = self.get_originals_storage()
        originals_storage.clear_category(category)
        sip_storage = self.get_sip_storage()
        sip_storage.clear_category(category)

    def list(self, stage: StagingDirectories, category: Optional[FileCategoryDirectories]):
        stage_storage = self.get_stage_storage(stage)
        return [str(p) for p in stage_storage.list(category)]

    def list_sip_contents(self, path=None):
        if path is None:
            path = self.sip_contents_dir
            name = 'archive'
        else:
            name = path.name
        contents = {'label': name, 'contents': []}
        for p in path.iterdir():
            if p.is_dir():
                contents['contents'].append(self.list_sip_contents(p))
            else:
                contents['contents'].append({'label': p.name})
        return contents

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

    def _add_to_sip(self, name, content, category: FileCategoryDirectories):
        sip_storage = self.get_sip_storage()
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

        msgs = originals_storage.log_save(name, content)
        if msgs.has_errors:
            return msgs
        msgs.append(self._add_to_sip(name=name, content=content, category=category))
        if msgs.has_errors:
            self.delete(category, Path(content.name))

        return msgs

    def get_or_create_sip_bag(self, bagit_info):
        logger.info("creating bagit metadata")
        sip_dir = str(self.sip_dir)
        try:
            bag = fs.make_bag(sip_dir, bagit_info)
            bag.save(manifests=True)
        except RuntimeError as e:
            # FIXME: is this still needed?
            # Temporary hack to get around a bagit error that changes
            # the working directory
            logger.exception(e)
            logger.info("creating bagit metadata failed. moving on")
            logger.info("moved to wrong directory: %s", os.getcwd())
            os.chdir('/code')
            logger.info("reset working directory to: %s", os.getcwd())

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
                msgs.append(self._add_to_sip(name=str(name), content=f, category=category))

        return msgs

    def build_aip(self, sip_dir: Optional[str] = None):
        logger.info("building aip")
        if sip_dir is None:
            sip_dir = str(self.sip_dir)
        shutil.rmtree(str(self.aip_dir), ignore_errors=True)
        shutil.copytree(sip_dir, str(self.aip_dir))

    def build_archive_at_dest(self, dest):
        logger.info("building archive")
        self.build_aip()
        if self.aip_contents_dir.exists():
            with zipfile.ZipFile(dest, 'w') as archive:
                for root_path, dirs, file_paths in os.walk(str(self.aip_contents_dir)):
                    for file_path in file_paths:
                        path = Path(root_path, file_path)
                        archive.write(str(path), arcname=str(path.relative_to(self.aip_contents_dir)))
            logger.info("building archive succeeded")
            return True
        else:
            logger.error("building archive failed - no aip directory")
            return False

    def build_archive(self, force=False):
        if not self.archivepath.exists() or force:
            self.build_archive_at_dest(dest=str(self.archivepath))

    def rebuild(self):
        msgs = self.build_sip()
        self.build_archive(force=True)
        return msgs


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
                msgs.downgrade()
        except Exception as e:
            msgs.append(create_fs_message(str(e), StagingDirectories.sip, MessageLevels.error))
        return msgs


def import_archive(codebase_release, nestedcode_folder_name, fs_api=None):
    if fs_api is None:
        fs_api = codebase_release.get_fs_api()
    archive_name = '{}.zip'.format(nestedcode_folder_name)
    shutil.make_archive(nestedcode_folder_name, 'zip', nestedcode_folder_name)
    with open(archive_name, 'rb') as f:
        msgs = fs_api.add(FileCategoryDirectories.code, content=f, name="nestedcode.zip")
    return msgs
