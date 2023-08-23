import os
import re
import json
import logging
import modelcluster.fields
import pandas as pd

from collections import defaultdict
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.dispatch import receiver
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.urls import reverse
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from taggit.models import Tag

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


class UserSpamStatusQuerySet(models.QuerySet):
    def filter_by_user_ids(self, user_ids, **kwargs):
        return self.filter(member_profile__user_id__in=user_ids, **kwargs)


class UserSpamStatus(models.Model):
    member_profile = models.OneToOneField(
        MemberProfile, on_delete=models.CASCADE, primary_key=True
    )
    # FIXME: add help_text
    # None = not processed yet
    # True = bio_classifier considered this user to be spam
    # False = bio_classifier did not consider this user to be spam
    labelled_by_text_classifier = models.BooleanField(default=None, null=True)
    text_classifier_confidence = models.FloatField(default=0)

    # similar to bio_classifier
    labelled_by_user_classifier = models.BooleanField(default=None, null=True)
    user_classifier_confidence = models.FloatField(default=0)

    labelled_by_curator = models.BooleanField(default=None, null=True)
    last_updated = models.DateField(auto_now=True)
    is_training_data = models.BooleanField(default=False)

    objects = UserSpamStatusQuerySet.as_manager()

    @staticmethod
    def get_recommendations_sorted_by_confidence():
        return UserSpamStatus.objects.all().order_by("text_classifier_confidence")

    def __str__(self):
        return "user={}, labelled_by_text_classifier={}, text_classifier_confidence={}, labelled_by_user_classifier={}, user_classifier_confidence={}, labelled_by_curator={}, last_updated={}, is_training_data={}".format(
            str(self.member_profile),
            str(self.labelled_by_text_classifier),
            str(self.text_classifier_confidence),
            str(self.labelled_by_user_classifier),
            str(self.user_classifier_confidence),
            str(self.labelled_by_curator),
            str(self.last_updated),
            str(self.is_training_data),
        )


# Create a new UserSpamStatus whenever a new MemberProfile is created
@receiver(post_save, sender=MemberProfile)
def sync_member_profile_spam(sender, instance, **kwargs):
    UserSpamStatus(member_profile=instance).save()


class UserSpamStatusProcessor:
    """
    converts UserSpamStatus querysets into Pandas dataframes
    """

    def __init__(self):
        self.db_column_names = [
            "member_profile__user_id",
            "member_profile__user__first_name",
            "member_profile__user__last_name",
            "member_profile__user__is_active",
            "member_profile__user__email",
            "member_profile__timezone",
            "member_profile__affiliations",
            "member_profile__bio",
            "member_profile__research_interests",
            "member_profile__personal_url",
            "member_profile__professional_url",
            "labelled_by_curator",
            "labelled_by_text_classifier",
            "labelled_by_user_classifier",
            "text_classifier_confidence",
            "user_classifier_confidence",
        ]

        self.column_names = [
            "user_id",
            "first_name",
            "last_name",
            "is_active",
            "email",
            "timezone",
            "affiliations",
            "bio",
            "research_interests",
            "personal_url",
            "professional_url",
        ]

        self.type_int_bool_column_names = [
            "member_profile__user_id",
            "labelled_by_curator",
            # "labelled_by_text_classifier",
            # "labelled_by_user_classifier",
            # "text_classifier_confidence",
            # "user_classifier_confidence",
        ]

    def __rename_columns(self, df):
        if df.empty:
            return df
        df.rename(
            columns=dict(zip(self.db_column_names, self.column_names)),
            inplace=True,
        )
        return df

    def __convert_df_markup_to_string(self, df):
        if df.empty:
            return df
        for col in df.columns:
            if col in self.type_int_bool_column_names:
                df[col] = df[col].fillna(0).astype(int)
                # It is safe to set Nan as 0 because:
                # for training, all values with labelled_by_curator=None are exclueded before passed to this function.
                # for prediction, the labelled_by_curator column is not used during prediction process.
            else:
                df[col] = df[col].apply(
                    lambda text: re.sub(r"<.*?>", " ", str(text))
                )  # Removing markdown
        return df

    def get_all_users_df(self):
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None, labelled_by_curator=None)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_unlabelled_by_curator_df(self):
        # return : DataFrame of user data that haven't been labeled by curator
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None)
                        .filter(labelled_by_curator=None)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_untrained_df(self):
        # return : DataFrame of user data that haven't been used for train previously
        return self.__rename_columns(
            self.__convert_df_markup_to_string(
                pd.DataFrame(
                    list(
                        UserSpamStatus.objects.all()
                        .exclude(member_profile__user_id=None, labelled_by_curator=None)
                        .filter(is_training_data=False)
                        .values(*self.db_column_names)
                    )
                )
            )
        )

    def get_unlabelled_users(self):
        unlabelled_users = list(
            UserSpamStatus.objects.filter(
                Q(labelled_by_curator=None)
                & Q(labelled_by_text_classifier=None)
                & Q(labelled_by_user_classifier=None)
            )
        )
        return unlabelled_users

    # FIXME: tune confidence threshold later
    def get_spam_users(self, confidence_threshold=0.5):
        """
        This functions will first filter out the users with labelled_by_curator==True,
        but the ones with None, only get users with labelled_by_user_classifier == True
        or labelled_by_text_classifier == True with a specific confidence level.
        """
        spam_users = list(
            UserSpamStatus.objects.filter(
                Q(labelled_by_curator=True)
                | Q(labelled_by_text_classifier=True)
                & Q(text_classifier_confidence__gte=confidence_threshold)
                | Q(labelled_by_user_classifier=True)
                & Q(user_classifier_confidence__gte=confidence_threshold)
            ).values_list("member_profile__user_id", flat=True)
        )
        return spam_users  # returns list of spam user_id

    def have_labelled_by_curator(self):
        # if there are users with labelled_by_curator != None, return True
        if UserSpamStatus.objects.filter(
            Q(labelled_by_curator=True) | Q(labelled_by_curator=False)
        ).exists():
            return True
        return False

    def all_have_labels(self):
        # returns True if all users have any kind of labels (labelled_by_curator, user_meta_classifier, text_classifier)
        # if all users have any kind of labels (labelled_by_curator, user_meta_classifier, text_classifier), return True
        return UserSpamStatus.objects.filter(
            Q(labelled_by_curator=None)
            | Q(labelled_by_user_classifier=None)
            | Q(labelled_by_text_classifier=None)
        )

    def load_labels_from_csv(self, training_file=None):
        if training_file is None:
            training_file = settings.SPAM_TRAINING_DATASET_PATH
        """
        updates UserSpamStatus.labelled_by_curator based on an initial training file.
        Dataset should have columns "user_id" and "is_spam" indicating their spam status
        param : path to a training dataset to be loaded
        return : list of user_ids marked as spam via UserSpamStatus.labelled_by_curator 
        """
        label_df = pd.read_csv(training_file)  # FIXME: add exception handling
        nonspam_user_ids = label_df[label_df["is_spam"] == 0]["user_id"]
        spam_user_ids = label_df[label_df["is_spam"] == 1]["user_id"]
        UserSpamStatus.objects.filter_by_user_ids(nonspam_user_ids).update(
            labelled_by_curator=False
        )
        UserSpamStatus.objects.filter_by_user_ids(spam_user_ids).update(
            labelled_by_curator=True
        )
        return list(spam_user_ids)

    def update_training_data(self, df, training_data=True):
        # param : DataFrame of user_ids (int) that were used to train a model
        # return : None
        for idx, row in df.iterrows():
            UserSpamStatus.objects.filter(
                member_profile__user_id=row["user_id"]
            ).update(is_training_data=training_data)

    def update_predictions(self, prediction_df, is_text_classifier=False):
        # params : prediction_df ... a Dataframe with columns "user_id", "labelled_by_{}", and "{}_classifier_confidence"
        # return : None
        if is_text_classifier:
            for idx, row in prediction_df.iterrows():
                UserSpamStatus.objects.filter(
                    member_profile__user_id=row.user_id
                ).update(
                    labelled_by_text_classifier=row.labelled_by_text_classifier,
                    text_classifier_confidence=row.text_classifier_confidence,
                )
        else:
            for idx, row in prediction_df.iterrows():
                UserSpamStatus.objects.filter(
                    member_profile__user_id=row.user_id
                ).update(
                    labelled_by_user_classifier=row.labelled_by_user_classifier,
                    user_classifier_confidence=row.user_classifier_confidence,
                )
