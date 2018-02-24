from django.db import transaction

from .models import PendingTagCleanup, TagProxy

acronyms = [
    ('cellular automata', 'ca'),
    ('complex adaptive system', 'cas'),
    ('genetic algorithm', 'ga'),
    ('belief desire intention', 'bdi')
]


@transaction.atomic
def load_initial_data():
    for (r, l) in acronyms:
        PendingTagCleanup.objects.create(new_names=[r], old_names=[l])
    PendingTagCleanup.objects.process()

    PendingTagCleanup.objects.bulk_create(PendingTagCleanup.find_groups_by_porter_stemmer())
    # Keep system dynamics tag separate from dynamic systems
    ptc = PendingTagCleanup.objects.get(new_names__contains=['dynamic systems'])
    ptc.old_names = [name for name in ptc.old_names if name != 'system dynamics']
    ptc.save()
    PendingTagCleanup.objects.process()

    PendingTagCleanup.objects.bulk_create(PendingTagCleanup.find_groups_by_platform_and_language())
    PendingTagCleanup.objects.process()

    # Ad Hoc Deletions
    regexes = [r'^jdk', r'^(?:ms|microsoft v)', r'^\.net', r'^version', 'r^visual s', 'r^jbuilder', r'^\d+\.',
               r'^length>']
    for regex in regexes:
        TagProxy.objects.filter(name__iregex=regex).to_tag_cleanup()

    # Couldn't figure out what this abm platform is
    PendingTagCleanup.objects.create(new_names=['LPL'], old_names=['LPL 5.55'])

    PendingTagCleanup.objects.process()
