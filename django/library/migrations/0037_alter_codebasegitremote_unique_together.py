# Generated by Django 4.2.17 on 2025-02-07 19:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0036_codebasegitremote_is_preexisting_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="codebasegitremote",
            unique_together={("owner", "repo_name")},
        ),
    ]
