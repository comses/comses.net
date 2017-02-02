""" migrate Drupal filesystem data into the new library structure """

import datetime
import logging
import os
import re
import shutil

import pygit2
from django.contrib.auth.models import User

from library import fs
from library.models import Codebase, CodebaseRelease

logger = logging.getLogger(__name__)


class ModelVersionFileset:

    OPENABM_VERSIONDIRS_MAP = {
        'dataset': 'data',
        'sensitivity': 'results'
        # one to one mappings for doc and code
    }

    def __init__(self, basedir, version_number: int):
        self.basedir = basedir
        self.semver = '1.{0}.0'.format(version_number - 1)

    def migrate(self, release: CodebaseRelease):
        logger.debug("migrating %s with %s", self.semver, release)
        working_directory_path = str(release.workdir_path)
        submitted_package_path = str(release.submitted_package_path())
        # copy basedirs over verbatim into the working directory
        shutil.copytree(self.basedir, working_directory_path)
        for codebase_version_dir in os.scandir(working_directory_path):
            # codebase version directory = code/ doc/ dataset/ sensitivity/ directories
            for f in os.scandir(codebase_version_dir.path):
                destination_dir = self.OPENABM_VERSIONDIRS_MAP.get(codebase_version_dir.name,
                                                                   codebase_version_dir.name)
                destination_path = str(release.submitted_package_path(destination_dir))
                if fs.is_archive(f.name):
                    logger.debug("unpacking archive %s to %s", f.path, destination_path)
                    shutil.unpack_archive(f.path, destination_path)
                else:
                    os.makedirs(destination_path, exist_ok=True)
                    shutil.copy(f.path, destination_path)

        # clean up garbage / system metadata files
        for root, dirs, files in os.walk(submitted_package_path, topdown=True):
            if root == '__MACOSX':
                # special case for parent __MACOSX system files, skip
                logger.debug("deleting mac os x system directory")
                shutil.rmtree(root)
            else:
                # otherwise, scan and remove any system files
                removed_files = fs.rm_system_files(root, dirs, files)
                if removed_files:
                    logger.warning("Deleted system files: %s", removed_files)
        # create bagit bags on the sips
        release.get_or_create_sip_bag()
        # FIXME: clean up working_directory_path eventually


class ModelFileset:

    VERSION_REGEX = re.compile('\d+')

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
        return candidate.is_dir() and candidate.name.startswith('v') and ModelFileset.VERSION_REGEX.search(candidate.name)

    def migrate(self):
        codebase = Codebase.objects.get(identifier=self._model_id)
        for version in self._versions:
            logger.debug("Migrating codebase %s v%s", codebase.title, version.semver)
            release = codebase.releases.get(version_number=version.semver)
            version.migrate(release)
        media_dir = str(codebase.media_dir())
        os.makedirs(media_dir, exist_ok=True)
        for media_dir_entry in self._media:
            shutil.copy(media_dir_entry.path, media_dir)
            codebase.images.append({
                'name': media_dir_entry.name,
                'path': media_dir,
                'url': codebase.media_url(media_dir_entry.name),
            })
        codebase.save()


def load(src_dir: str):
    logger.debug("MIGRATING %s", src_dir)
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


def get_or_create_repo(full_path: str) -> pygit2.Repository:
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
        repo = pygit2.init_repository(full_path, bare=True)
    else:
        repo = pygit2.discover_repository(full_path)
    return repo


def create_signature(creator: User):
    return pygit2.Signature(creator.get_full_name(), creator.email)


def move_content(repo, model_version):
    pass


def commit(repo: pygit2.Repository, message, creator: User):
    signature = create_signature(creator)

    index = repo.index
    index.read()
    index.add_all()

    index.write()
    tree = index.write_tree()

    today = datetime.date.today().strftime("%B %d, %Y")

    parents = [repo.head.get_object().hex]

    sha = repo.create_commit('refs/head/master',
                             signature,
                             signature,
                             message,
                             tree,
                             parents)

    return sha
