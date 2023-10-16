import json
import logging
import os
import re

from collections import defaultdict
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.urls import reverse
from modelcluster import fields
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from taggit.models import Tag

from library.models import ProgrammingLanguage, CodebaseReleasePlatformTag

logger = logging.getLogger(__name__)

PENDING_TAG_CLEANUPS_FILENAME = "pending_tag_cleanups"


def has_parental_object_content_field(model):
    try:
        field = model._meta.get_field("content_object")
        return isinstance(field, fields.ParentalKey)
    except FieldDoesNotExist:
        return False


def get_through_tables():
    return [
        m.related_model
        for m in Tag._meta.related_objects
        if isinstance(m, models.ManyToOneRel)
        and has_parental_object_content_field(m.related_model)
    ]


class TagCuratorProxyQuerySet(models.QuerySet):
    def with_comma(self):
        return self.filter(name__icontains=",")

    def programming_languages(self):
        return self.filter(
            id__in=ProgrammingLanguage.objects.values_list("tag_id", flat=True)
        )

    def platforms(self):
        return self.filter(
            id__in=CodebaseReleasePlatformTag.objects.values_list("tag_id", flat=True)
        )

    def with_and(self):
        return self.filter(name__iregex=" +and +")

    def with_uppercase(self):
        return self.filter(name__regex=r"[A-Z]+")

    def ending_in_version_numbers(self):
        return self.filter(name__iregex=r"^(.* |)(se\\-|r)?[\d.v]+[ab]?$")

    def to_tag_cleanups(self, new_name=""):
        tag_cleanups = []
        for old_tag in self.iterator():
            tag_cleanups.append(TagCleanup(new_name=new_name, old_name=old_tag.name))
        return tag_cleanups


class TagCuratorProxy(Tag):
    objects = TagCuratorProxyQuerySet.as_manager()

    class Meta:
        proxy = True


class TagCleanupQuerySet(models.QuerySet):
    @transaction.atomic
    def process(self):
        migrator = TagMigrator()
        tag_cleanups = self.filter(transaction_id__isnull=True)
        tag_groupings = (
            tag_cleanups.values("old_name")
            .annotate(new_names=ArrayAgg("new_name"))
            .order_by("old_name")
        )
        for tag_grouping in tag_groupings:
            logger.debug(
                "tag cleanup: %s => %s",
                tag_grouping["old_name"],
                tag_grouping["new_names"],
            )
            migrator.migrate(
                old_name=tag_grouping["old_name"], new_names=tag_grouping["new_names"]
            )
        tct = TagCleanupTransaction.objects.create()
        tag_cleanups.update(transaction=tct)

    def create_comma_split(self):
        tags = TagCuratorProxy.objects.with_comma()
        for tag in tags:
            new_names = [re.sub(r"!\w+", " ", t.strip()) for t in tag.name.split(",")]
            yield TagCleanup(new_names=new_names, old_names=[tag.name])

    def dump(self, filepath):
        tag_cleanups = []
        for tag_cleanup in self.iterator():
            tag_cleanups.append(tag_cleanup.to_dict())

        os.makedirs(str(filepath.parent), exist_ok=True)
        with filepath.open("w") as f:
            json.dump(tag_cleanups, f, indent=4, sort_keys=True)


# Should just use file system to find ground truth
class Matcher:
    def __init__(self, name, regex):
        self.name = name
        self.regex = regex


def pl_regex(name, flags=re.IGNORECASE):
    return re.compile(
        r"\b{}(?:,|\b|\s+|\Z|v?\d+\.\d+\.\d+(?:-?\w[\w-]*)*|\d+)".format(name),
        flags=flags,
    )


PLATFORM_AND_LANGUAGE_MATCHERS = [
    Matcher("AnyLogic", pl_regex("anylogic")),
    Matcher("C", pl_regex(r"(?<!objective[-\s])c(?!(?:\+\+|#))")),
    Matcher("Cormas", pl_regex("cormas")),
    Matcher("C++", pl_regex(r"v?c\+\+")),
    Matcher("C#", pl_regex("c#")),
    Matcher("DEVS Suite", pl_regex("devs suite")),
    Matcher("GRASS", pl_regex("grass")),
    Matcher("Excel", pl_regex("excel")),
    Matcher("GAMA", pl_regex("(?:gama?l|gama)")),
    Matcher("Groovy", pl_regex("groovy")),
    Matcher("Jade", pl_regex("jade")),
    Matcher("Jason", pl_regex("jason")),
    Matcher("Java", pl_regex("java")),
    Matcher("James II", pl_regex("james\\s+ii")),
    Matcher("Logo", pl_regex("logo")),
    Matcher("NetLogo", pl_regex("netlogo")),
    Matcher("Mason", pl_regex("mason")),
    Matcher("Mathematica", pl_regex("mathematica")),
    Matcher("MatLab", pl_regex("matlab")),
    Matcher("Objective-C", pl_regex(r"objective(:?[-\s]+)?c")),
    Matcher("Pandora", pl_regex("pandora")),
    Matcher("Powersim Studio", pl_regex("powersim\\s+studio")),
    Matcher("Python", pl_regex("python")),
    Matcher("R", pl_regex("r")),
    Matcher("Repast", pl_regex("repast")),
    Matcher("ReLogo", pl_regex("relogo")),
    Matcher("SciLab", pl_regex("scilab")),
    Matcher("SocLab", pl_regex("soclab")),
    Matcher("Stella", pl_regex("stella")),
    Matcher("Smalltalk", pl_regex("smalltalk")),
    Matcher("Stata", pl_regex("stata")),
    Matcher("VBA", pl_regex("vba")),
]

VERSION_NUMBER_MATCHER = re.compile(
    r"^(?:[\d.x_()\s>=<\\/^]|version|update|build|or|higher|beta|alpha|rc)+$"
)


class TagCleanupTransaction(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.date_created.strftime("%c")


class TagCleanup(models.Model):
    new_name = models.CharField(max_length=300, blank=True)
    old_name = models.CharField(max_length=300)
    transaction = models.ForeignKey(
        TagCleanupTransaction, null=True, blank=True, on_delete=models.SET_NULL
    )

    objects = TagCleanupQuerySet.as_manager()

    def __str__(self):
        return f"id={self.id} new_name={self.new_name}, old_name={self.old_name}"

    @classmethod
    def find_groups_by_porter_stemmer(cls):
        ps = PorterStemmer()
        names = [
            (
                tag,
                frozenset(
                    ps.stem(token)
                    for token in word_tokenize(tag)
                    if token not in stopwords.words("english")
                ),
            )
            for tag in Tag.objects.order_by("name").values_list("name", flat=True)
        ]

        groups = defaultdict(lambda: [])
        for tag in names:
            groups[tag[1]].append(tag[0])

        tag_cleanups = []
        for k, old_names in groups.items():
            if len(old_names) > 1:
                min_name_len = min(len(name) for name in old_names)
                smallest_names = sorted(
                    name for name in old_names if len(name) == min_name_len
                )
                new_name = smallest_names[0]
                old_names.remove(new_name)
                for old_name in old_names:
                    tag_cleanups.append(
                        TagCleanup(new_name=new_name, old_name=old_name)
                    )

        return tag_cleanups

    @classmethod
    def find_groups_by_platform_and_language(cls):
        tag_cleanups = []
        for tag in (
            TagCuratorProxy.objects.programming_languages()
            .union(TagCuratorProxy.objects.platforms())
            .order_by("name")
            .iterator()
        ):
            new_names = []
            for matcher in PLATFORM_AND_LANGUAGE_MATCHERS:
                match = matcher.regex.search(tag.name)
                if match and tag.name != matcher.name:
                    new_names.append(matcher.name)
            if not new_names:
                if not VERSION_NUMBER_MATCHER.search(tag.name):
                    continue
            for new_name in new_names:
                tag_cleanups.append(TagCleanup(new_name=new_name, old_name=tag.name))
        return tag_cleanups

    def to_dict(self):
        return {"new_name": self.new_name, "old_name": self.old_name}

    @staticmethod
    def load_from_dict(dct):
        return TagCleanup(new_name=dct["new_name"], old_name=dct["old_name"])

    @classmethod
    def load(cls, filepath):
        with filepath.open("r") as f:
            tag_cleanups = json.load(f, object_hook=cls.load_from_dict)
        return tag_cleanups

    @classmethod
    def process_url(cls):
        return reverse("curator:process_tagcleanups")

    class Meta:
        permissions = (("process_tagcleanup", "Able to process tag cleanups"),)


class TagMigrator:
    def __init__(self):
        self.through_models = get_through_tables()

    @classmethod
    def create_new_tags(cls, new_names):
        nonexisting_new_names = new_names.difference(
            Tag.objects.filter(name__in=new_names).values_list("name", flat=True)
        )
        # Generating a unique slug without appending unique a id requires adding tags one by one
        for name in nonexisting_new_names:
            tag = Tag(name=name)
            tag.save()

    @staticmethod
    def copy_through_model_refs(model, new_tags, old_tag):
        pks = list(
            model.objects.filter(tag=old_tag).values_list("content_object", flat=True)
        )
        through_instances = []
        for pk in pks:
            for new_tag in new_tags:
                through_instances.append(model(tag=new_tag, content_object_id=pk))
        model.objects.bulk_create(through_instances)

    def migrate(self, new_names, old_name):
        through_models = self.through_models
        new_names = set(new_names).difference(old_name).difference({""})
        self.create_new_tags(new_names)
        new_tags = Tag.objects.filter(name__in=new_names).order_by("name")
        old_tag = Tag.objects.filter(name=old_name).first()
        logger.info("Mapping %s -> %s", old_name, new_names)
        if old_tag is not None:
            for model in through_models:
                self.copy_through_model_refs(model, new_tags=new_tags, old_tag=old_tag)
            old_tag.delete()


class TagCluster(models.Model):
    canonical_tag_name = models.TextField()
    tags = models.ManyToManyField(Tag)
    confidence_score = models.FloatField()
    date_created = models.DateTimeField(auto_now_add=True, null=True)

    def add_tag_by_name(self, name: str):
        tag = Tag.objects.filter(name=name)
        if tag:
            self.tags.add(tag.first())
        return tag

    def save_mapping(self):
        canonical_tag, _ = CanonicalTag.objects.get_or_create(
            name=self.canonical_tag_name
        )

        previous_tag_mappings = CanonicalTagMapping.objects.filter(
            canonical_tag=canonical_tag
        )
        previous_tag_mappings.delete()

        tag_mappings = [
            CanonicalTagMapping(
                tag=tag,
                canonical_tag=canonical_tag,
                confidence_score=self.confidence_score,
            )
            for tag in self.tags.all()
        ]
        for tag_mapping in tag_mappings:
            tag_mapping.save()

        return canonical_tag, tag_mappings

    def __str__(self):
        return f"canonical_tag_name={self.canonical_tag_name} tags={self.tags.all()}"


class CanonicalTag(models.Model):
    name = models.TextField(unique=True)

    def __str__(self):
        return f"name={self.name}"


class CanonicalTagMapping(models.Model):
    tag = models.OneToOneField(Tag, on_delete=models.deletion.CASCADE, primary_key=True)
    canonical_tag = models.ForeignKey(
        CanonicalTag, null=True, on_delete=models.SET_NULL
    )
    curator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confidence_score = models.FloatField()
    date_created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"tag={self.tag} canonical_tag={self.canonical_tag.name} confidence={self.confidence_score}"
