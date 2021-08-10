from pathlib import Path

from django.core.management.base import BaseCommand

from library.models import Codebase, CodebaseRelease


class Command(BaseCommand):
    help = "Summarize migration problems"

    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='Directory where codebase files are', default='/shared/library')

    def get_codebase_file_uuids(self, codebase_file_root):
        return set(model_dir.name for model_dir in codebase_file_root.iterdir() if model_dir.is_dir())

    def get_release_file_natural_keys(self, codebase_file_root):
        release_natural_keys = set()
        for codebase_dir in codebase_file_root.iterdir():
            releases_dir = codebase_dir.joinpath('releases')
            if releases_dir.is_dir():
                for release_dir in releases_dir.iterdir():
                    if release_dir.is_dir():
                        release_pk = int(release_dir.name)
                        release_natural_keys.add(
                            (codebase_dir.name, release_pk))
        return release_natural_keys

    def handle(self, *args, **options):
        model_file_root = Path(options['directory'])

        codebase_file_natural_keys = self.get_codebase_file_uuids(model_file_root)
        codebase_natural_keys = set(str(uuid) for uuid in Codebase.objects.values_list('uuid', flat=True))
        models_without_codebase = codebase_file_natural_keys.difference(codebase_natural_keys)
        codebases_without_model_folder = codebase_natural_keys.difference(codebase_file_natural_keys)

        release_file_natural_keys = self.get_release_file_natural_keys(model_file_root)
        release_natural_keys = set((str(uuid), pk) for uuid, pk in CodebaseRelease.objects.values_list('codebase__uuid', 'pk'))
        release_files_without_release = release_file_natural_keys.difference(release_natural_keys)
        releases_without_release_files = release_natural_keys.difference(release_file_natural_keys)

        print('Checks\n')

        print('\nCodebase folder without codebase ({})'.format(len(models_without_codebase)))
        print(sorted(list(models_without_codebase)))

        print('\nCodebase without codebase folder ({})'.format(len(codebases_without_model_folder)))
        print(sorted(list(codebases_without_model_folder)))

        print('\nRelease folder without release ({})'.format(len(release_files_without_release)))
        print(sorted(list(release_files_without_release)))

        print('\nReleases without release folder ({})'.format(len(releases_without_release_files)))
        print(sorted(list(releases_without_release_files)))
