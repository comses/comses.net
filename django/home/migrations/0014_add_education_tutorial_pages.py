# Generated by Django 3.2.16 on 2022-11-14 19:37

import core.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import home.models
import modelcluster.contrib.taggit
import modelcluster.fields


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailimages", "0024_index_image_file_hash"),
        ("home", "0013_increase_summary_length"),
        ("wagtailcore", "0069_log_entry_jsonfield"),
        ("taggit", "0004_alter_taggeditem_content_type_alter_taggeditem_tag"),
    ]

    operations = [
        migrations.CreateModel(
            name="EducationPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "template",
                    models.CharField(default="home/education.jinja", max_length=256),
                ),
                (
                    "heading",
                    models.CharField(
                        help_text="Short name to be placed in introduction header.",
                        max_length=256,
                    ),
                ),
                (
                    "summary",
                    models.CharField(
                        help_text="Markdown-enabled summary blurb for this page.",
                        max_length=5000,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(home.models.NavigationMixin, "wagtailcore.page"),
        ),
        migrations.CreateModel(
            name="TutorialCard",
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
                (
                    "sort_order",
                    models.IntegerField(blank=True, editable=False, null=True),
                ),
                (
                    "url",
                    models.CharField(
                        max_length=200,
                        verbose_name="Relative path, absolute path, or URL",
                    ),
                ),
                ("title", models.CharField(max_length=256)),
                (
                    "summary",
                    models.CharField(
                        blank=True,
                        help_text="Markdown-enabled summary for this tutorial card",
                        max_length=1000,
                    ),
                ),
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cards",
                        to="home.educationpage",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TutorialTag",
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
                (
                    "content_object",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tagged_items",
                        to="home.tutorialcard",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="home_tutorialtag_items",
                        to="taggit.tag",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="tutorialcard",
            name="tags",
            field=modelcluster.contrib.taggit.ClusterTaggableManager(
                blank=True,
                help_text="A comma-separated list of tags.",
                through="home.TutorialTag",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="tutorialcard",
            name="thumbnail_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
            ),
        ),
        migrations.CreateModel(
            name="TutorialDetailPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "heading",
                    models.CharField(
                        blank=True,
                        help_text="Large heading text placed on the blue background introduction header",
                        max_length=128,
                    ),
                ),
                (
                    "template",
                    models.CharField(default="home/tutorial.jinja", max_length=128),
                ),
                (
                    "post_date",
                    models.DateField(
                        default=django.utils.timezone.now, verbose_name="Post date"
                    ),
                ),
                (
                    "description",
                    core.fields.MarkdownField(
                        blank=True,
                        help_text="Markdown-enabled summary text placed below the heading and title.",
                        max_length=1024,
                        rendered_field=True,
                    ),
                ),
                (
                    "description_markup_type",
                    models.CharField(
                        choices=[
                            ("", "--"),
                            ("markdown", "markdown"),
                            ("html", "html"),
                            ("plain", "plain"),
                            ("", ""),
                        ],
                        default="markdown",
                        max_length=30,
                    ),
                ),
                (
                    "body",
                    core.fields.TutorialMarkdownField(
                        blank=True,
                        help_text="Markdown-enabled main content pane for this page.",
                        rendered_field=True,
                    ),
                ),
                ("_description_rendered", models.TextField(editable=False)),
                (
                    "body_markup_type",
                    models.CharField(
                        choices=[
                            ("", "--"),
                            ("markdown", "markdown"),
                            ("html", "html"),
                            ("plain", "plain"),
                            ("", ""),
                        ],
                        default="markdown",
                        max_length=30,
                    ),
                ),
                (
                    "jumbotron",
                    models.BooleanField(
                        default=True,
                        help_text="Mark as true if this page should display its title and description in a jumbotron",
                    ),
                ),
                ("_body_rendered", models.TextField(editable=False)),
            ],
            options={
                "abstract": False,
            },
            bases=(home.models.NavigationMixin, "wagtailcore.page"),
        ),
    ]
