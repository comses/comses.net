import pandas as pd
import random
import string
import os

from django.test import TestCase
from django.conf import settings

from curator.spam_classifiers import UserMetadataSpamClassifier, TextSpamClassifier
from curator.spam_processor import UserSpamStatusProcessor
from curator.models import UserSpamStatus
from core.models import MemberProfile
from core.models import User
from core.tests.base import UserFactory


class SpamDetectionTestCase(TestCase):
    def setUp(self):
        self.processor = UserSpamStatusProcessor()
        self.user_meta_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        self.user_factory = UserFactory()
        self.user_ids = self.create_new_users()

    def create_new_users(self):
        user_size = random.randint(5, 100)
        new_user_ids = []
        for i in range(0, user_size):
            new_user = self.user_factory.create()
            new_user_ids.append(new_user.id)
        return new_user_ids

    def add_texts_to_users(self, user_ids):
        for user_id in user_ids:
            letters = string.ascii_lowercase
            result_str = "".join(random.choice(letters) for i in range(10))
            MemberProfile.objects.all().filter(user_id=user_id).update(
                bio=result_str, research_interests=result_str
            )

    def delete_new_users(self, user_ids):
        for user_id in user_ids:
            user = User.objects.filter(id=user_id)
            user.delete()

    # def update_labels(self, user_ids):
    #     middle_idx = len(user_ids)/2 - 1
    #     label = True
    #     self.processor.update_labels(user_ids[0:middle_idx], label)
    #     label = False
    #     self.processor.update_labels(user_ids[middle_idx:-1], label)

    # def delete_labels(self, user_ids):
    #     self.processor.update_labels(user_ids, None)

    def update_labels(self, user_ids):
        for user_id in user_ids:
            label = random.randint(0, 1)
            self.processor.update_labels(user_id, label)

    def delete_labels(self, user_ids):
        for user_id in user_ids:
            self.processor.update_labels(user_id, None)

    def get_existing_user_ids(self):
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
            stub data/requirements ... ./curator/spam_dataset.csv
            assertion ... there exists users with label != None
        """
        self.processor.load_labels_from_csv()
        self.assertTrue(self.processor.labels_exist())

    # ============== Tests for UserSpamStatusProcessor.get_unlabel_df() ==============
    def test_get_label_df__new_users_added(self):
        """
        case1 : new user data added
            stub data/requirements ... new user data with label==None
            assertion ... no change in df
        """

        existing_user_ids = self.user_ids
        self.update_labels(
            existing_user_ids
        )  # make sure all the existing users have labels
        existing_df = self.processor.get_all_users_with_label()

        new_user_ids = self.create_new_users()  # default label==None

        user_size = len(new_user_ids) + len(existing_user_ids)
        new_df = self.processor.get_all_users_with_label()

        self.assertEqual(
            len(existing_df["user_id"].values), len(new_df["user_id"].values)
        )
        self.assertGreater(user_size, len(existing_df["user_id"].values))
        self.assertFalse(set(new_user_ids).issubset(set(new_df["user_id"].values)))
        self.delete_new_users(new_user_ids)

    def test_get_label_df__label_added(self):
        """
        case2 : new user data added
            stub data/requirements ... new user data with label==True/False
            assertion ... df with the specific columns with the addtional user data that were labelled.
        """
        existing_user_ids = self.user_ids
        self.update_labels(
            existing_user_ids
        )  # make sure all the existing users have labels

        new_user_ids = self.create_new_users()  # default label==None
        user_size = len(new_user_ids) + len(existing_user_ids)

        self.update_labels(new_user_ids)
        df = self.processor.get_all_users_with_label()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(
            set(self.processor.column_names).issubset(set(df.columns.unique()))
        )
        self.assertEqual(user_size, len(df["user_id"].values))
        self.assertTrue(set(new_user_ids).issubset(set(df["user_id"].values)))
        self.delete_new_users(new_user_ids)

    def test_get_label_df__no_users_added(self):
        """
        case3 : no new user data added
            stub data/requirements ... all data in DB with correct user_id has values
                                        with label==True/False
            assertion ... no change in df
        """
        existing_user_ids = self.user_ids
        self.update_labels(
            existing_user_ids
        )  # make sure all the existing users have labels
        existing_df = self.processor.get_all_users_with_label()

        self.update_labels(existing_user_ids)  # making sure all users are labelled

        new_df = self.processor.get_all_users_with_label()
        self.assertEqual(
            len(existing_df["user_id"].values), len(new_df["user_id"].values)
        )

    # ================================ Tests for UserMetadataSpamClassifier ================================
    def test_user_meta_classifier_fit(self):
        """
        stub data/requirements ... loaded labels (label) in DB using processor.load_labels_from_csv()
        assertion ... returns model metrics in the following format and output model instance as a pickle file
                      in the "/shared/curator/spam/" folder.
                      model metrics format = {"Accuracy": float,
                                                "Precision": float,
                                                "Recall": float,
                                                "F1",float,
                                                "test_user_ids": list of user_id}
        """
        user_ids = self.processor.load_labels_from_csv()
        self.update_labels(user_ids)

        user_meta_classifier_metrics = self.user_meta_classifier.fit()
        self.assertIsInstance(user_meta_classifier_metrics, dict)
        self.assertTrue("Accuracy" in user_meta_classifier_metrics)
        self.assertTrue("Precision" in user_meta_classifier_metrics)
        self.assertTrue("Recall" in user_meta_classifier_metrics)
        self.assertTrue("F1" in user_meta_classifier_metrics)
        self.assertTrue("test_user_ids" in user_meta_classifier_metrics)
        self.assertTrue(
            set(user_meta_classifier_metrics["test_user_ids"]).issubset(set(user_ids))
        )

        self.delete_labels(user_ids)

    def test_user_meta_classifier_prediction(self):
        """
        stub data/requirements ... /shared/curator/spam/{model}.pkl, and new user data on DB with label=None
        assertion ... True or False valuse in labelled_by_text_classifier and labelled_by_user_classifier fields
                        of the user data in DB
        """
        if not os.path.exists(self.user_meta_classifier.MODEL_METRICS_FILE_PATH):
            self.processor.load_labels_from_csv()
            self.user_meta_classifier.fit()

        existing_user_ids = self.user_ids
        self.update_labels(existing_user_ids)
        new_user_ids = self.create_new_users()  # default label==None
        labelled_user_ids, _ = self.user_meta_classifier.predict()

        # self.assertTrue(self.processor.all_have_labels())
        self.assertTrue(set(new_user_ids).issubset(labelled_user_ids))

    # ==================================== Tests for TextSpamClassifier ====================================
    def test_text_classifier_fit(self):
        user_ids = self.processor.load_labels_from_csv()
        self.add_texts_to_users(user_ids)
        self.update_labels(user_ids)

        text_classifier_metrics = self.text_classifier.fit()
        self.assertIsInstance(text_classifier_metrics, dict)
        self.assertTrue("Accuracy" in text_classifier_metrics)
        self.assertTrue("Precision" in text_classifier_metrics)
        self.assertTrue("Recall" in text_classifier_metrics)
        self.assertTrue("F1" in text_classifier_metrics)
        self.assertTrue("test_user_ids" in text_classifier_metrics)
        self.assertTrue(
            set(text_classifier_metrics["test_user_ids"]).issubset(set(user_ids))
        )

        self.delete_labels(user_ids)

    def test_text_classifier_prediction(self):
        if not os.path.exists(self.text_classifier.MODEL_METRICS_FILE_PATH):
            user_ids = self.processor.load_labels_from_csv()
            # self.add_texts_to_users(user_ids)
            self.text_classifier.fit()

        existing_user_ids = self.user_ids
        self.update_labels(existing_user_ids)
        new_user_ids = self.create_new_users()  # default label==None
        self.add_texts_to_users(existing_user_ids)
        self.add_texts_to_users(new_user_ids)
        labelled_user_ids, _ = self.text_classifier.predict()

        #self.assertTrue(self.processor.all_have_labels())
        self.assertTrue(bool(set(new_user_ids) & set(labelled_user_ids)))

    # # ============== Tests for UserSpamStatusProcessor.get_unlabel_df() ==============
    # def test_get_unlabel_df__new_users_added(self):
    #     """
    #     case1 : new user data added
    #         stub data/requirements ... new user data with label==None
    #         assertion ... df with the specific columns with the correct user_ids
    #     """

    #     existing_user_ids = self.user_ids
    #     user_ids = self.create_new_users()  # default label==None
    #     user_size = len(user_ids) + len(existing_user_ids)

    #     df = self.processor.get_unlabel_df()

    #     self.assertIsInstance(df, pd.DataFrame)
    #     self.assertTrue(
    #         set(self.processor.column_names).issubset(set(df.columns.unique()))
    #     )
    #     self.assertEqual(user_size, len(df["user_id"].values))
    #     self.assertTrue(set(user_ids).issubset(set(df["user_id"].values)))
    #     self.delete_new_users(user_ids)

    # def test_get_unlabel_df__no_users_added(self):
    #     """
    #     case2 : no new user data added
    #         stub data/requirements ... all data in DB with correct user_id has values
    #                                    with label!=None
    #         assertion ... empty df
    #     """
    #     existing_user_ids = self.user_ids
    #     self.update_labels(existing_user_ids)  # simulate a curator labelling the users

    #     df = self.processor.get_unlabel_df()
    #     self.assertEqual(len(df), 0)

    #     self.delete_labels(existing_user_ids)

    # ======================== Tests for UserSpamStatusProcessor.get_untrained_df()  ========================
    # def test_get_untrained_df__dataset_loaded(self):
    #     """
    #     case1 : Just uploaded spam_dataset.csv
    #         stub data/requirements ... just called load_labels_from_csv().
    #         assertion ... df with the specific columns with the correct user_ids
    #     """
    #     user_ids = self.processor.load_labels_from_csv()

    #     df = self.processor.get_untrained_df()
    #     self.assertIsInstance(df, pd.DataFrame)
    #     self.assertTrue(
    #         set(self.processor.column_names).issubset(set(df.columns.unique()))
    #     )
    #     # self.assertListEqual(user_ids, list(df["user_id"].values))
    #     self.assertTrue(set(user_ids) == set(list(df["user_id"].values)))
    #     self.delete_labels(user_ids)

    # def test_get_untrained_df__labels_updated(self):
    #     """
    #     case2 : label updated
    #         stub data/requirements ...  new labells by curator (users with abelled_by_curator!=None and is_training_data=False)
    #         assertion ... df with the specific columns with the correct user_ids
    #     """
    #     existing_user_ids = self.user_ids
    #     self.update_labels(existing_user_ids)  # update labels of exisiting users

    #     df = self.processor.get_untrained_df()
    #     self.assertIsInstance(df, pd.DataFrame)
    #     self.assertTrue(
    #         set(self.processor.column_names).issubset(set(df.columns.unique()))
    #     )
    #     # self.assertListEqual(existing_user_ids, list(df["user_id"].values))
    #     self.assertTrue(set(existing_user_ids) == set(list(df["user_id"].values)))
    #     self.delete_labels(existing_user_ids)

    # def test_get_untrained_df__no_labels_updated(self):
    #     """
    #     case3 : no label updates
    #         stub data/requirements ... all data in DB with label!=None has is_training_data=True
    #         assertion ... empty df
    #     """
    #     existing_user_ids = self.user_ids
    #     self.update_labels(existing_user_ids)  # update labels of exisiting users
    #     self.mark_as_training_data(existing_user_ids)  # mark the user as training data

    #     df = self.processor.get_untrained_df()
    #     self.assertEqual(len(df), 0)

    #     self.delete_labels(existing_user_ids)
    #     self.unmark_as_training_data(existing_user_ids)
