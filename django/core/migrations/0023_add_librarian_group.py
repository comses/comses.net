from django.db import migrations

LIBRARIAN_GROUP_NAME = "Librarian Users"


def create_librarian_group(apps, schema_editor):
    """
    ComsesGroups is a plain Enum over django.contrib.auth Groups, not a model field, so adding
    ComsesGroups.LIBRARIAN generates no schema migration. The Group row has to be created here or
    ComsesGroups.LIBRARIAN.get_group() raises Group.DoesNotExist in a deployed environment while
    every test that calls ComsesGroups.initialize() still passes.
    """
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=LIBRARIAN_GROUP_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_remove_socialmediasettings_twitter_account_and_more"),
        ("auth", "0001_initial"),
    ]

    operations = [
        # deliberately irreversible-as-a-no-op: deleting the Group would cascade through
        # auth_user_groups and silently strip every membership an admin had assigned
        migrations.RunPython(create_librarian_group, migrations.RunPython.noop),
    ]
