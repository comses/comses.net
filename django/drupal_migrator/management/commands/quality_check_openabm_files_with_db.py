from pathlib import Path

from django.core.management.base import BaseCommand

from drupal_migrator.utils import is_version_dir
from library.models import Codebase, CodebaseRelease


class Command(BaseCommand):
    help = "Summarize migration problems"

    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='Directory where openabm models are', default='/shared/incoming/models')

    def get_model_ids(self, model_file_root):
        return set(model_dir.name for model_dir in model_file_root.iterdir() if model_dir.is_dir())

    def get_modelversion_natural_keys(self, model_file_root):
        release_natural_keys = set()
        for model_dir in model_file_root.iterdir():
            if model_dir.is_dir():
                for release_dir in model_dir.iterdir():
                    vd = is_version_dir(release_dir)
                    if vd:
                        modelversion = int(vd.group(0)) - 1
                        release_natural_keys.add(
                            (model_dir.name, '1.{}.0'.format(modelversion)))
        return release_natural_keys

    def handle(self, *args, **options):
        model_file_root = Path(options['directory'])

        model_natural_keys = self.get_model_ids(model_file_root)
        codebase_natural_keys = set(Codebase.objects.values_list('identifier', flat=True))
        models_without_codebase = model_natural_keys.difference(codebase_natural_keys)
        codebases_without_model_folder = codebase_natural_keys.difference(model_natural_keys)

        modelversion_natural_keys = self.get_modelversion_natural_keys(model_file_root)
        release_natural_keys = set(CodebaseRelease.objects.values_list('codebase__identifier', 'version_number'))
        modelversions_without_release = modelversion_natural_keys.difference(release_natural_keys)
        releases_without_modelversion_folder = release_natural_keys.difference(modelversion_natural_keys)

        print('Checks\n')

        print('\nModels without codebases ({})'.format(len(models_without_codebase)))
        print(sorted(list(models_without_codebase)))

        print('\nCodebase without model folder ({})'.format(len(codebases_without_model_folder)))
        print(sorted(list(codebases_without_model_folder)))

        print('\nModelVersions without release ({})'.format(len(modelversions_without_release)))
        print(sorted(list(modelversions_without_release)))

        print('\nReleases without modelversion folder ({})'.format(len(releases_without_modelversion_folder)))
        print(sorted(list(releases_without_modelversion_folder)))