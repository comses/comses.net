# Generated by Django 4.2.11 on 2024-05-10 23:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_event_is_marked_spam_job_is_marked_spam_spamcontent_and_more"),
        ("library", "0026_alter_codebasereleaseplatformtag_tag_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="codebase",
            name="is_marked_spam",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="codebase",
            name="spam_content",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.spamcontent",
            ),
        ),
    ]
