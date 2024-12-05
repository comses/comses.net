import bagit
import hashlib
import os
from collections import OrderedDict
from tempfile import TemporaryDirectory


def fsck(queryset):
    results = OrderedDict()
    for release in queryset:
        rfsc = CodebaseReleaseFileConsistencyChecker(release)
        errors = rfsc.check()
        if errors:
            results[release.id] = release, errors
    return results


def pretty_print_fsck_results(results):
    for id, result in results.items():
        release, errors = result
        print(f"ID: {id}")
        print(f"Release: {release}")
        print("Errors:")
        for error in errors:
            if isinstance(error, FileNotFoundError):
                error_msg = f"FileNotFoundError({error.filename})"
            else:
                error_msg = error
            print(f"    {error_msg}")
        print("\n")


def hash_file(path, chunk_size=65536):
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            sha256.update(data)
    return sha256


class CodebaseReleaseFileConsistencyChecker:
    def __init__(self, release):
        self.release = release
        self.fs_api = self.release.get_fs_api()

    def check_fixity_of_aip(self):
        if self.release.is_published:
            bag = bagit.Bag(str(self.fs_api.aip_dir))
            bag.validate()

    def check_fixity_of_archive(self):
        # generate archive.zip into temporary location and compare hashes
        if self.release.is_published:
            with TemporaryDirectory() as d:
                new_archive_path = os.path.join(d, "archive.zip")
                aip_exists = self.fs_api.build_archive_at_dest(new_archive_path)
                if not aip_exists:
                    raise IOError("AIP directory does not exist")
                new_archive_hash = hash_file(new_archive_path)
                old_archive_hash = hash_file(str(self.fs_api.archivepath))
                return new_archive_hash.hexdigest() == old_archive_hash.hexdigest()

    def check(self):
        errors = []
        try:
            self.check_fixity_of_aip()
        except Exception as e:
            errors.append(e)

        try:
            self.check_fixity_of_archive()
        except Exception as e:
            errors.append(e)

        return errors
