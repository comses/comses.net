# Generated by Django 4.2.17 on 2025-01-09 20:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0032_license_text_codemeta_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="CodebaseGitMirror",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date_created", models.DateTimeField(auto_now_add=True)),
                ("last_modified", models.DateTimeField(auto_now=True)),
                ("repository_name", models.CharField(max_length=100, unique=True)),
                (
                    "remote_url",
                    models.URLField(
                        blank=True, help_text="URL of mirrored remote repository"
                    ),
                ),
                ("last_local_update", models.DateTimeField(blank=True, null=True)),
                ("last_remote_update", models.DateTimeField(blank=True, null=True)),
                (
                    "user_access_token",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                (
                    "organization_login",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "local_releases",
                    models.ManyToManyField(
                        related_name="+", to="library.codebaserelease"
                    ),
                ),
                (
                    "remote_releases",
                    models.ManyToManyField(
                        related_name="+", to="library.codebaserelease"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="codebase",
            name="git_mirror",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="codebase",
                to="library.codebasegitmirror",
            ),
        ),
    ]