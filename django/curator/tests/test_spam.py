import pandas as pd
import random

from django.test import TestCase

from core.models import User
from core.tests.base import UserFactory
from curator.spam import SpamDetector
from curator.models import UserSpamStatus


class SpamDetectionTestCase(TestCase):
    def setUp(self):
        self.spam_detector = SpamDetector()
        self.user_factory = UserFactory()
        self.user_ids = self.create_new_users()

    @property
    def processor(self):
        return self.spam_detector.processor

    @property
    def user_metadata_classifier(self):
        return self.spam_detector.user_metadata_classifier

    @property
    def text_classifier(self):
        return self.spam_detector.text_classifier

    def create_new_users(self):
        user_size = random.randint(5, 100)
        new_user_ids = []
        for i in range(0, user_size):
            new_user = self.user_factory.create()
            new_user_ids.append(new_user.id)
        return new_user_ids

    def delete_new_users(self, user_ids):
        for user_id in range(0, len(user_ids)):
            user = User.objects.filter(id=user_id)
            user.delete()

    def randomize_user_spam_labels(self, user_ids):
        """
        randomly partition user_ids into spam and non-spam
        spam = 1, non-spam = 0
        """

        '''
        something similar in raw SQL
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE curator_userspamstatus
                SET labelled_by_curator = random() > 0.5
                WHERE user_id IN %s
                """,
                [tuple(user_ids)],
            )
        '''
        randomized_user_ids = list(user_ids)
        random.shuffle(randomized_user_ids)
        partition_index = len(user_ids) // 3
        spam_ids = randomized_user_ids[partition_index:]
        non_spam_ids = randomized_user_ids[:partition_index]
        UserSpamStatus.objects.filter_by_user_ids(non_spam_ids).update(
            labelled_by_curator=False
        )
        UserSpamStatus.objects.filter_by_user_ids(spam_ids).update(
            labelled_by_curator=True
        )

    def delete_labels(self, user_ids):
        UserSpamStatus.objects.filter_by_user_ids(user_ids).update(
            labelled_by_curator=None
        )

    def get_existing_users(self):
        user_ids = list(
            UserSpamStatus.objects.all()
            .exclude(member_profile__user_id=None)
            .values_list("member_profile__user_id", flat=True)
        )
        return user_ids

    def mark_as_training_data(self, user_ids):
        df = pd.DataFrame(user_ids, columns=["user_id"])
        self.processor.update_training_data(df)

    def unmark_as_training_data(self, user_ids):
        df = pd.DataFrame(user_ids, columns=["user_id"])
        self.processor.update_training_data(df, training_data=False)

    # =================  Tests for UserSpamStatusProcessor.load_labels_from_csv() =================
    def test_load_labels_from_csv(self):
        """
        case : First time loading spam_dataset.csv
            stub data/requirements ... /shared/curator/spam/spam_dataset.csv
            assertion ... there exists users with labelled_by_curator != None
        """
        self.processor.load_labels_from_csv()
        self.assertTrue(self.processor.have_labelled_by_curator())

    # ============== Tests for UserSpamStatusProcessor.get_unlabelled_by_curator_df() ==============
    def test_get_unlabelled_by_curator_df__new_users_added(self):
        """
        case1 : new user data added
            stub data/requirements ... new user data with labelled_by_curator==None
            assertion ... df with the specific columns with the correct user_ids
        """

        existing_users = self.user_ids
        user_ids = self.create_new_users()  # default labelled_by_curator==None
        user_size = len(user_ids) + len(existing_users)

        df = self.processor.get_unlabelled_by_curator_df()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(
            set(self.processor.column_names).issubset(set(df.columns.unique()))
        )
        self.assertEqual(user_size, len(df["user_id"].values))
        self.assertTrue(set(user_ids).issubset(set(df["user_id"].values)))
        self.delete_new_users(user_ids)

    def test_get_unlabelled_by_curator_df__no_users_added(self):
        """
        case2 : no new user data added
            stub data/requirements ... all data in DB with correct user_id has values
                                       with labelled_by_curator!=None
            assertion ... empty df
        """
        existing_users = self.user_ids
        self.randomize_user_spam_labels(
            existing_users
        )  # simulate a curator labelling the users

        df = self.processor.get_unlabelled_by_curator_df()
        self.assertEqual(len(df), 0)

        self.delete_labels(existing_users)

    # ======================== Tests for UserSpamStatusProcessor.get_untrained_df()  ========================
    def test_get_untrained_df__dataset_loaded(self):
        """
        case1 : Just uploaded spam_dataset.csv
            stub data/requirements ... just called load_labels_from_csv().
            assertion ... df with the specific columns with the correct user_ids
        """
        user_ids = self.processor.load_labels_from_csv()

        df = self.processor.get_untrained_df()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(
            set(self.processor.column_names).issubset(set(df.columns.unique()))
        )
        self.assertCountEqual(user_ids, list(df["user_id"].values))

        self.delete_labels(user_ids)

    def test_get_untrained_df__labels_updated(self):
        """
        case2 : labelled_by_curator updated
            stub data/requirements ...  new labells by curator (users with abelled_by_curator!=None and is_training_data=False)
            assertion ... df with the specific columns with the correct user_ids
        """
        existing_users = self.user_ids
        self.randomize_user_spam_labels(
            existing_users
        )  # update labels of exisiting users

        df = self.processor.get_untrained_df()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(
            set(self.processor.column_names).issubset(set(df.columns.unique()))
        )
        self.assertCountEqual(existing_users, list(df["user_id"].values))

        self.delete_labels(existing_users)

    def test_get_untrained_df__no_labels_updated(self):
        """
        case3 : no label updates
            stub data/requirements ... all data in DB with labelled_by_curator!=None has is_training_data=True
            assertion ... empty df
        """
        existing_users = self.user_ids
        self.randomize_user_spam_labels(
            existing_users
        )  # update labels of exisiting users
        self.mark_as_training_data(existing_users)  # mark the user as training data

        df = self.processor.get_untrained_df()
        self.assertEqual(len(df), 0)

        self.delete_labels(existing_users)
        self.unmark_as_training_data(existing_users)

    # ================================ Tests for UserMetadataSpamClassifier ================================
    def test_user_metadata_classifier_fit(self):
        """
        stub data/requirements ... loaded labels (labelled_by_curator) in DB using processor.load_labels_from_csv()
        assertion ... returns model metrics in the following format and output model instance as a pickle file
                      in the "/shared/curator/spam/" folder.
                      model metrics format = {"Accuracy": float,
                                                "Precision": float,
                                                "Recall": float,
                                                "F1",float,
                                                "test_user_ids": list of user_id}
        """
        user_ids = self.processor.load_labels_from_csv()

        user_metadata_classifier_metrics = self.user_metadata_classifier.fit()
        self.assertIsInstance(user_metadata_classifier_metrics, dict)
        self.assertTrue("Accuracy" in user_metadata_classifier_metrics)
        self.assertTrue("Precision" in user_metadata_classifier_metrics)
        self.assertTrue("Recall" in user_metadata_classifier_metrics)
        self.assertTrue("F1" in user_metadata_classifier_metrics)
        self.assertTrue("test_user_ids" in user_metadata_classifier_metrics)
        self.assertTrue(
            set(user_metadata_classifier_metrics["test_user_ids"]).issubset(
                set(user_ids)
            )
        )

        self.delete_labels(user_ids)

    def test_user_metadata_classifier_prediction(self):
        """
        stub data/requirements ... /shared/curator/spam/{model}.pkl, and new user data on DB with labelled_by_curator=None
        assertion ... True or False valuse in labelled_by_text_classifier and labelled_by_user_classifier fields
                        of the user data in DB
        """
        if not self.user_metadata_classifier.MODEL_METRICS_FILE_PATH.is_file():
            self.processor.load_labels_from_csv()
            self.user_metadata_classifier.fit()

        existing_users = self.user_ids
        self.randomize_user_spam_labels(existing_users)
        new_user_ids = self.create_new_users()  # default labelled_by_curator==None
        labelled_user_ids = self.user_metadata_classifier.predict()

        self.assertTrue(self.processor.all_have_labels())
        self.assertTrue(set(new_user_ids).issubset(labelled_user_ids))

    # ==================================== Tests for TextSpamClassifier ====================================
    # TODO : Remove commentout once TextSpamClassifier is ready
    # def test_text_classifier_fit(self):
    #     user_ids = self.processor.load_labels_from_csv()

    #     text_classifier_metrics = self.text_classifier.fit()
    #     self.assertIsInstance(text_classifier_metrics, dict)
    #     self.assertTrue("Accuracy" in text_classifier_metrics)
    #     self.assertTrue("Precision" in text_classifier_metrics)
    #     self.assertTrue("Recall" in text_classifier_metrics)
    #     self.assertTrue("F1" in text_classifier_metrics)
    #     self.assertTrue("test_user_ids" in text_classifier_metrics)
    #     self.assertTrue(set(text_classifier_metrics["test_user_ids"]).issubset(set(user_ids)))

    #     self.delete_labels(user_ids)

    # def test_text_classifier_prediction(self):
    #     if not self.text_classifier.MODEL_METRICS_FILE_PATH.is_file():
    #             self.processor.load_labels_from_csv()
    #             self.text_classifier.fit()

    #     existing_users = self.user_ids
    #     self.update_labels(existing_users)
    #     new_user_ids = self.create_new_users() # default labelled_by_curator==None
    #     labelled_user_ids = self.text_classifier.predict()

    #     self.assertTrue(self.processor.all_have_labels())
    #     self.assertTrue(set(new_user_ids).issubset(labelled_user_ids))
