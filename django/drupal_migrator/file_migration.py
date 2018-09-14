""" migrate Drupal filesystem data into the new library structure """

import logging
import os
import re
import shutil

from django.conf import settings

from core import fs
from drupal_migrator.utils import model_version_has_files, is_version_dir
from library import fs as library_fs
from library.fs import MessageLevels
from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


class ModelVersionFileset:
    OPENABM_VERSIONDIRS_MAP = {
        'code': library_fs.FileCategoryDirectories.code,
        'dataset': library_fs.FileCategoryDirectories.data,
        'doc': library_fs.FileCategoryDirectories.docs,
        'sensitivity': library_fs.FileCategoryDirectories.results
        # one to one mappings for doc and code
    }

    def __init__(self, basedir, version_number: int):
        self.basedir = basedir
        self.semver = '1.{0}.0'.format(version_number - 1)

    def model_version_has_files(self):
        return model_version_has_files(self.basedir)

    def log_msgs(self, msgs):
        if msgs:
            msgs.downgrade()
            logs, level = msgs.serialize()
            for log in logs:
                getattr(logger, log['level'])(log['msg']['detail'])

    def migrate(self, release: CodebaseRelease):
        logger.debug("Migrating %s (v%s)", release, self.semver)
        if not self.model_version_has_files():
            logger.warning("no files found for release")
            return
        fs_api = release.get_fs_api(mimetype_mismatch_message_level=MessageLevels.debug)
        fs_api.initialize()
        for src_dirname in os.scandir(self.basedir):
            src = os.path.join(self.basedir, src_dirname.name)
            category = self.OPENABM_VERSIONDIRS_MAP.get(src_dirname.name)
            if category is None:
                logger.error("Bad directory name {} for release {} {}. Skipping".format(
                    src_dirname.name, release.codebase.title, release.version_number))
            else:
                logger.debug("migrating category %s" % category.name)
                msgs = fs_api.add_category(category, src)
                self.log_msgs(msgs)

        msgs = fs_api.build_sip()
        self.log_msgs(msgs)
        fs_api.get_or_create_sip_bag(release.bagit_info)
        fs_api.build_aip()
        fs_api.build_archive()


class ModelFileset:
    def __init__(self, model_id: int, dir_entry):
        self._model_id = model_id
        self._dir_entry = dir_entry
        self._versions = []
        self._media = []
        for f in os.scandir(dir_entry.path):
            vd = self.is_version_dir(f)
            if vd:
                self._versions.append(ModelVersionFileset(f.path, int(vd.group(0))))
            elif fs.is_media(f.path):
                self._media.append(f)
            else:
                logger.warning("unexpected file in %s: %s", dir_entry.path, f)

    @staticmethod
    def is_version_dir(candidate):
        return is_version_dir(candidate)

    def migrate(self):
        codebase = Codebase.objects.get(identifier=self._model_id)
        logger.debug("Migrating %s with %s versions", codebase, len(self._versions))
        codebase.media = []
        for version in self._versions:
            try:
                release = codebase.releases.get(version_number=version.semver)
            except CodebaseRelease.DoesNotExist:
                logger.exception('CodebaseRelease does not exist {}'.format(self._dir_entry))
                continue
            version.migrate(release)
        # FIXME: in 3.6, os.makedirs will accept media_dir as a path-like object
        media_dir = str(codebase.upload_path)
        if self._media:
            os.makedirs(media_dir, exist_ok=True)
            for media_dir_entry in self._media:
                with open(media_dir_entry.path, 'rb') as file_entry:
                    logger.info('importing media file: %s', file_entry.name)
                    codebase.import_media(file_entry, images_only=False)
                shutil.copy(media_dir_entry.path, media_dir)
        codebase.save()


def load(src_dir: str):
    logger.debug("MIGRATING %s", src_dir)
    # FIXME: use a mandatory argument to force deleting of release data. Don't want to delete data by accident
    fs.clean_directory(settings.LIBRARY_ROOT)
    shutil.register_unpack_format('rar', ['.rar'], fs.unrar)
    for dir_entry in os.scandir(src_dir):
        if dir_entry.is_dir():
            try:
                model_id = int(dir_entry.name)
                logger.debug("processing %s", dir_entry.path)
                mfs = ModelFileset(model_id, dir_entry)
                mfs.migrate()
            except:
                logger.exception("Un-model-library-like directory: %s", dir_entry.name)


def sanitize_name(name: str) -> str:
    return re.sub(r"\W+", "_", name)
