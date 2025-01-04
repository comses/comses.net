# Generated by Django 4.2.17 on 2025-01-06 21:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0035_codebasegitmirror_date_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="codebase",
            name="codemeta_json",
            field=models.JSONField(
                default=dict,
                help_text="JSON metadata conforming to the codemeta schema. Cached as of the last update",
            ),
        ),
        migrations.AddField(
            model_name="codebaserelease",
            name="codemeta_json",
            field=models.JSONField(
                default=dict,
                help_text="JSON metadata conforming to the codemeta schema. Cached as of the last update",
            ),
        ),
    ]