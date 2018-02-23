import logging
import re
from collections import defaultdict

import modelcluster.fields
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.utils.functional import cached_property
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from taggit.models import Tag, TaggedItemBase

from library.models import ProgrammingLanguage

logger = logging.getLogger(__name__)


def has_parental_object_content_field(model):
    try:
        field = model._meta.get_field('content_object')
        return isinstance(field, modelcluster.fields.ParentalKey)
    except models.FieldDoesNotExist:
        return False


def get_through_tables():
    return [m.related_model for m in Tag._meta.related_objects if
            isinstance(m, models.ManyToOneRel) and has_parental_object_content_field(m.related_model)]


class TagProxyQuerySet(models.QuerySet):
    def with_comma(self):
        return self.filter(name__icontains=',')

    def for_programming_languages(self):
        return self.filter(id__in=ProgrammingLanguage.objects.values_list('id', flat=True))

    def with_and(self):
        return self.filter(name__iregex=' +and +')

    def with_uppercase(self):
        return self.filter(name__regex=r'[A-Z]+')

    def ending_in_version_numbers(self):
        return self.filter(name__iregex=r'^(.* |)(se\\-|r)?[\d.v]+[ab]?$')

    def create_tag_candidate(self, names):
        return PendingTagCleanup(new_names=names, original_names=list(self.values_list('name', flat=True)))


class TagProxy(Tag):
    objects = TagProxyQuerySet.as_manager()

    class Meta:
        proxy = True


class CanonicalName(models.Model):
    original = models.CharField(max_length=300)
    canonical = models.CharField(max_length=300)


class PendingTagGroupingQuerySet(models.QuerySet):
    @transaction.atomic
    def process(self):
        tag_groupings = self.select_for_update().order_by('id')
        for tag_grouping in tag_groupings:
            tag_grouping.group()
        tag_groupings.delete()

    def create_comma_split(self):
        tags = TagProxy.objects.with_comma()
        for tag in tags:
            new_names = [re.sub(r'!\w+', ' ', t.strip()) for t in tag.name.split(',')]
            yield PendingTagCleanup(new_names=new_names, old_names=[tag.name])


class PendingTagCleanup(models.Model):
    # is_active = models.BooleanField(default=True)
    new_names = ArrayField(models.CharField(max_length=300))
    old_names = ArrayField(models.CharField(max_length=300))

    objects = PendingTagGroupingQuerySet.as_manager()

    def __str__(self):
        return 'id={} new_names={}, old_names={}'.format(self.id, self.new_names, self.old_names)

    def create_new_tags(self, new_names):
        nonexisting_new_names = new_names.difference(
            Tag.objects.filter(name__in=new_names).values_list('name', flat=True))
        # Generating a unique slug without appending unique a id requires adding tags one by one
        for name in nonexisting_new_names:
            tag = Tag(name=name)
            tag.save()

    @staticmethod
    def move_through_model_refs(m, new_tags, old_tags):
        pks = list(m.objects.filter(tag__in=old_tags).values_list('content_object', flat=True).distinct())
        through_instances = []
        for pk in pks:
            for new_tag in new_tags:
                through_instances.append(m(tag=new_tag, content_object_id=pk))
        m.objects.bulk_create(through_instances)

    @cached_property
    def THROUGH_TABLES(self):
        return get_through_tables()

    @classmethod
    def dumps(cls):

    @classmethod
    def find_groups_by_porter_stemmer(cls, save=False):
        ps = PorterStemmer()
        names = [(tag, frozenset(ps.stem(token) for token in word_tokenize(tag)
                                 if token not in stopwords.words('english')))
                 for tag in Tag.objects.order_by('name').values_list('name', flat=True)]

        groups = defaultdict(lambda: [])
        for tag in names:
            groups[tag[1]].append(tag[0])

        tag_cleanups = []
        for k, names in groups.items():
            if len(names) > 1:
                min_name_len = min(len(name) for name in names)
                smallest_names = sorted(name for name in names if len(name) == min_name_len)
                new_names = [smallest_names[0]]
                tag_cleanups.append(PendingTagCleanup(new_names=new_names, old_names=names))

        if save:
            PendingTagCleanup.objects.bulk_create(tag_cleanups)

        return tag_cleanups

    @classmethod
    def group_all(cls):
        for tag_cleanup in cls.objects.iterator():
            tag_cleanup.group()

    def group(self):
        """Combine or split original taggit tags to form new tags"""
        through_models = self.THROUGH_TABLES

        new_names = set(self.new_names)
        old_names = set(self.old_names)
        common_names = new_names.intersection(old_names)
        new_names.difference_update(common_names)
        old_names.difference_update(common_names)

        self.create_new_tags(new_names)
        new_tags = Tag.objects.filter(name__in=list(new_names))
        old_tags = Tag.objects.filter(name__in=list(old_names))
        for m in through_models:
            self.move_through_model_refs(m, new_tags, old_tags)
        old_tags.delete()
