import os
import re
import json
import pickle
import logging
import itertools
from typing import List
from urllib.parse import urlparse
from collections import defaultdict

import modelcluster.fields
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models, transaction
from django.urls import reverse
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from taggit.models import Tag

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pandas

from core.models import MemberProfile

from library.models import ProgrammingLanguage, CodebaseReleasePlatformTag

logger = logging.getLogger(__name__)

PENDING_TAG_CLEANUPS_FILENAME = "pending_tag_cleanups"


def has_parental_object_content_field(model):
    try:
        field = model._meta.get_field("content_object")
        return isinstance(field, modelcluster.fields.ParentalKey)
    except models.FieldDoesNotExist:
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


def pl_regex(name, flags=re.I):
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
    Matcher("James II", pl_regex("james\s+ii")),
    Matcher("Logo", pl_regex("logo")),
    Matcher("NetLogo", pl_regex("netlogo")),
    Matcher("Mason", pl_regex("mason")),
    Matcher("Mathematica", pl_regex("mathematica")),
    Matcher("MatLab", pl_regex("matlab")),
    Matcher("Objective-C", pl_regex(r"objective(:?[-\s]+)?c")),
    Matcher("Pandora", pl_regex("pandora")),
    Matcher("Powersim Studio", pl_regex("powersim\s+studio")),
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
        return "{}".format(self.date_created.strftime("%c"))


class TagCleanup(models.Model):
    new_name = models.CharField(max_length=300, blank=True)
    old_name = models.CharField(max_length=300)
    transaction = models.ForeignKey(
        TagCleanupTransaction, null=True, blank=True, on_delete=models.SET_NULL
    )

    objects = TagCleanupQuerySet.as_manager()

    def __str__(self):
        return "id={} new_name={}, old_name={}".format(
            self.id, repr(self.new_name), repr(self.old_name)
        )

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

class SpamRecommendation(models.Model):
    member_profile = models.OneToOneField(MemberProfile, on_delete=models.CASCADE, primary_key=True)
    is_spam_labelled_by_classifier = models.BooleanField(default=False)
    is_spam_labelled_by_curator = models.BooleanField(default=False)
    is_labelled_by_curator_before = models.BooleanField(default=False)
    classifier_confidence = models.FloatField(default=0)
    last_updated_date = models.DateField(auto_now=True)

    @staticmethod
    def get_recommendations_sorted_by_confidence():
        return SpamRecommendation.objects.all().order_by('classifier_confidence')
    
    def __str__(self):
        return "user={}, user_bio={}, is_spam_labelled_by_classifier={}, is_spam_labelled_by_curator={}, is_labelled_by_curator_before={}, classifier_confidence={}, last_updated_date={}".format(
            str(self.member_profile), 
            str(self.member_profile.bio), 
            str(self.is_spam_labelled_by_classifier), 
            str(self.is_spam_labelled_by_curator), 
            str(self.is_labelled_by_curator_before),
            str(self.classifier_confidence),
            str(self.last_updated_date)
        )

from curator.spam_detect import UserPipeline
class BioSpamClassifier(object):
    # This is temporary until we find a better solution.
    # We are saving and loading models straight to the VM,
    # ideally, we instead store it in some object storage instead.
    INITIAL_FILE_PATH = "curator/label.json"
    MODEL_FILE_PATH = "curator/instance.pkl"

    @staticmethod
    def load_model(): 
        if os.path.isfile(BioSpamClassifier.MODEL_FILE_PATH): BioSpamClassifier().fit_on_initial_data()
        with open(BioSpamClassifier.MODEL_FILE_PATH, "rb") as file:
            return pickle.load(file)

    def __init__(self):
        self.pipeline = Pipeline([
            ('cleaner', FunctionTransformer(BioSpamClassifier.text_list_cleanup)),
            ('countvectorizer', CountVectorizer()),
            ('classifier', MultinomialNB())
        ])

    def fit_on_initial_data(self):
        training_data = pandas.read_json(BioSpamClassifier.INITIAL_FILE_PATH)
        x_train, y_train = training_data['bio'], training_data['is_spam']
        self.pipeline.fit(x_train, y_train)
        self.save_model()

    def fit_on_curator_labelled_recommendations(self):
        curator_labelled_recommendations = SpamRecommendation.objects.exclude(is_spam_labelled_by_curator=False)

        # TODO: I should split these up into their own functions 
        x_data = [[recommendation.bio] for recommendation in curator_labelled_recommendations]
        y_data = [1 if recommendation.is_spam else 0 for recommendation in curator_labelled_recommendations]

        self.pipeline.fit(x_data, y_data)

    def predict_spam(self, text : str):
        # Since our classifier classifies based on the user's bio, if it is empty, there is nothing we can predict about it.
        if len(text) == 0: return None, (0, 0)
        spam_probabilities = self.pipeline.predict_proba([text])[0]
        return BioSpamClassifier.__argmax(spam_probabilities), spam_probabilities

    def predict_row(self, row):
        prediction, probabilities = self.predict_spam(row['bio'])
        row['is_spam_labelled_by_classifier'] = prediction
        row['classifier_confidence'] = abs(probabilities[0] - probabilities[1])
        row['is_spam_labelled_by_curator'] = False
        return row

    def predict_all_unlabelled_users(self):
        bio_spam_classifier = BioSpamClassifier.load_model()
        user_pipeline = UserPipeline()
        unlabelled_users = user_pipeline.filtered_by_labelled_df(is_labelled=True)
        unlabelled_users = unlabelled_users.apply(lambda row : self.predict_row(row), axis=1)
        return unlabelled_users

    def save_model(self): 
        with open(BioSpamClassifier.MODEL_FILE_PATH, "wb") as file:
            pickle.dump(self, file)

    def text_list_cleanup(text_list : List[str]): 
        return [BioSpamClassifier.text_cleanup_pipeline(text) for text in text_list]

    def text_cleanup_pipeline(text : str): 
        text = str(text)
        text = BioSpamClassifier.__convert_text_to_lowercase(text)
        text = BioSpamClassifier.__replace_urls_with_webtag(text)
        text = BioSpamClassifier.__replace_numbers_with_zero(text)
        text = BioSpamClassifier.__remove_markdown(text)
        text = BioSpamClassifier.__remove_excess_spaces(text)
        return text
    
    # Helper functions
    def __argmax(float_list : List[float]):
        map_index_to_element = lambda index: float_list[index]
        return max(range(len(float_list)), key=map_index_to_element)
    
    def __convert_text_to_lowercase(text : str): return text.lower()
    def __replace_urls_with_webtag(text : str): return re.sub(r'http\S+|www\S+', ' webtag ', text) 
    def __replace_numbers_with_zero(text : str): return re.sub(r'\d+', ' 0 ', text)
    def __remove_markdown(text : str): return re.sub(r'<.*?>', ' ', text)
    def __remove_excess_spaces(text : str): return re.sub(r'\s+', ' ', text)