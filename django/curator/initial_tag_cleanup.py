from django.db import transaction

from .models import TagCleanup, TagCuratorProxy

acronyms = [
    ('cellular automata', 'ca'),
    ('complex adaptive system', 'cas'),
    ('genetic algorithm', 'ga'),
    ('belief desire intention', 'bdi')
]


@transaction.atomic
def load_initial_data():
    for (r, l) in acronyms:
        TagCleanup.objects.create(new_name=r, old_name=l)
    TagCleanup.objects.process()

    TagCleanup.objects.bulk_create(TagCleanup.find_groups_by_porter_stemmer())
    bad_translations = [
        ('dynamic systems', 'system dynamics'),
        ('effect size', 'size effect'),
        ('from', 'other')
    ]
    for bad_translation in bad_translations:
        TagCleanup.objects.get(new_name=bad_translation[0], old_name=bad_translation[1]).delete()
    TagCleanup.objects.process()

    TagCleanup.objects.bulk_create(TagCleanup.find_groups_by_platform_and_language())
    TagCleanup.objects.process()

    # Ad Hoc Deletions
    regexes = [r'^jdk', r'^(?:ms|microsoft v)', r'^\.net', r'^version', r'^visual s', 'r^jbuilder', r'^\d+\.?',
               r'^length>', r'^from$', r'^other$', r'[<=>]+\s+\d+', r'^jbulider', '^window', '^ubuntu']
    for regex in regexes:
        TagCleanup.objects.bulk_create(TagCuratorProxy.objects.filter(name__iregex=regex).to_tag_cleanups())

    # Couldn't figure out what this abm platform is
    TagCleanup.objects.create(new_name='LPL', old_name='LPL 5.55')

    TagCleanup.objects.process()

    # Query related data
    pgcli_command = \
        """
        \copy (select name, count(*) as tag_count
        from
            (select tag.name as name, codebase.id as codebase_id
            from
                (select content_object_id as release_id, tag_id
                from library_codebasereleaseplatformtag
                union
                select content_object_id, tag_id
                from library_programminglanguage) as release_tags

                inner join library_codebaserelease as release on release_tags.release_id = release.id
                inner join library_codebase as codebase on release.codebase_id = codebase.id
                inner join taggit_tag as tag on release_tags.tag_id = tag.id

                group by tag.name, codebase.id) as tags_by_codebase
            where name not in ('agent based model (abm)', 'ps-i v5', 'Any', 'English')
            group by name
            having count(*) > 0
            order by count(*) desc)
        to 'programming_language_and_platform_counts_by_codebase.csv' delimiter ',' csv header;
        """
