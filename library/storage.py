from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from hashfs import HashFS

import logging
import os
import pathlib

logger = logging.getLogger(__name__)


@deconstructible
class HashStorage(Storage):

    def __init__(self, root=None):
        if root is None:
            root = settings.HASH_STORAGE_ROOT
        self.root = root
        self._fs = HashFS(self.root, depth=3, width=2)

    def _open(self, name, mode='rb'):
        return self._fs.open(name, mode)

    def _save(self, name, content):
        extension = ''.join(pathlib.Path(name).suffixes)
        hash_address = self._fs.put(content, extension=extension)
        logger.debug("saved content with name %s and extension %s to %s", name, content, hash_address)
        return hash_address.relpath

    def delete(self, name):
        return self._fs.delete(name)

    def exists(self, name):
        return self._fs.exists(name)

    def path(self, name):
        return self._fs.get(name).abspath

