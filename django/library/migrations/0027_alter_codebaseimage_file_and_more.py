# Generated by Django 4.2.7 on 2024-02-15 17:03

import django.core.files.storage
from django.db import migrations, models
import library.models
import wagtail.images.models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0026_alter_codebasereleaseplatformtag_tag_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codebaseimage",
            name="file",
            field=models.ImageField(
                height_field="height",
                storage=django.core.files.storage.FileSystemStorage(
                    location="/code/library/tests/tmp/library"
                ),
                upload_to=wagtail.images.models.get_upload_to,
                verbose_name="file",
                width_field="width",
            ),
        ),
        migrations.AlterField(
            model_name="codebaserelease",
            name="submitted_package",
            field=models.FileField(
                max_length=1000,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(
                    location="/code/library/tests/tmp/library"
                ),
                upload_to=library.models.Codebase._release_upload_path,
            ),
        ),
    ]
