# Generated by Django 3.2.13 on 2022-06-21 22:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0016_codebasereleasedownload_reason"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codebasereleasedownload",
            name="reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("research", "Research"),
                    ("education", "Education"),
                    ("commercial", "Commercial"),
                    ("policy", "Policy / Planning"),
                    ("other", "Other, please specify below"),
                ],
                max_length=500,
            ),
        ),
    ]
