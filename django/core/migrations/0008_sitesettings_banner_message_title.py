# Generated by Django 2.2.12 on 2020-04-23 02:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_mailchimp_digest_archive_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="banner_message_title",
            field=models.CharField(
                blank=True, default="CoMSES Net Notice", max_length=64
            ),
        ),
    ]
