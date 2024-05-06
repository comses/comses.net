import pandas as pd
import random
import string
import os
from django.test import TestCase
from django.conf import settings
from django.db import connection

from curator.spam_classifiers import (
    XGBoostClassifier, 
    CountVectEncoder, 
    CategoricalFieldEncoder
    )
from curator.spam_processor import UserSpamStatusProcessor
from curator.models import UserSpamStatus, UserSpamPrediction
from curator.spam import SpamDetectionContext, PresetContextID
from core.models import MemberProfile, User
from core.tests.base import UserFactory
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from nltk.parse.generate import generate, demo_grammar
from nltk import CFG
from xgboost import XGBClassifier

SPAM_DIR_PATH = settings.SPAM_DIR_PATH

class SpamDetectionTestCase(TestCase):
    def setUp(self):
        self.processor = UserSpamStatusProcessor()
        self.user_factory = UserFactory()
        self.user_ids = self.create_new_users()

    def create_new_users(self):
        user_size = random.randint(5, 30)
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
        self.processor.update_training_data(df, is_training_data=False)

    def get_mock_binary_dataset(self, split=True):
        dataset = load_breast_cancer(as_frame=True)
        if not split:
            return (dataset.data, dataset.target.to_frame(name="target"))
        return train_test_split(dataset.data, dataset.target, test_size=0.1, random_state=434)

    def get_mock_text_dataset(self, split=True, sample_size=10):
        grammar = CFG.fromstring(demo_grammar)
        sentences = [' '.join(sentence) for sentence in generate(grammar, n=sample_size)]
        target = [random.randint(0, 1) for i in range(len(sentences))]
        dataset = pd.DataFrame({'data':sentences, 'target':target})
        if not split:
            return (dataset[['data']], dataset[['target']])
        return train_test_split(dataset.data, dataset.target, test_size=0.1, random_state=434)

        
    # ================= Tests for UserSpamStatusProcessor =================
    def test_load_labels_from_csv(self):
        """
        Verify the functionality of loading labels from a CSV file.
        The test checks if the labels are correctly applied to users in the database.
        Preconditions:
          - Assumes a CSV file at ./curator/spam_dataset.csv with 'user_id' and 'label' columns.
        Postconditions:
          - Asserts that there are users with labels in the database, indicating successful label application.
        """
        self.processor.load_labels_from_csv()
        self.assertTrue(self.processor.labels_exist())
    
    def test_get_all_users(self):
        """
        Verify that all users can be retrieved with the 'email' field processed into 'email_username' and 'email_domain'.
        Preconditions:
          - User data must include 'email' that can be split into username and domain.
        Assertions:
          - Ensure the resulting dataframe is not empty.
          - Assert that the dataframe includes the processed columns 'email_username' and 'email_domain'.
        """
        selected_fields = ["email"]
        df = self.processor.get_all_users(selected_fields)
        self.assertFalse(df.empty)
        self.assertTrue(set(['email_username', 'email_domain']).issubset(set(df.columns)))

    def test_get_selected_users(self):
        """
        Verify that selected users are retrieved with the 'email' field processed into 'email_username' and 'email_domain'.
        Preconditions:
          - Random subset of user IDs used to fetch data.
        Assertions:
          - Ensure the resulting dataframe is not empty.
          - Assert that the dataframe includes the necessary 'email_username' and 'email_domain' columns.
        """
        selected_fields = ["email"]
        user_ids = random.sample(self.user_ids, min(len(self.user_ids), 5))
        df = self.processor.get_selected_users(user_ids, selected_fields)
        self.assertFalse(df.empty)
        self.assertTrue(set(['email_username', 'email_domain']).issubset(set(df.columns)))

    def test_get_all_users_with_label(self):
        """
        Verify that all users with labels are retrieved along with the 'email' field processed.
        Preconditions:
          - Labels are assigned to all user IDs prior to retrieval.
        Assertions:
          - Ensure the resulting dataframe is not empty.
          - Assert that 'email_username', 'email_domain', and 'label' columns are present.
        """
        self.update_labels(self.user_ids)
        selected_fields = ["email"]
        df = self.processor.get_all_users_with_label(selected_fields)
        self.assertFalse(df.empty)
        self.assertTrue(set(['email_username', 'email_domain']).issubset(set(df.columns)))
        self.assertTrue("label" in df.columns)

    def test_get_selected_users_with_label(self):
        """
        Verify that selected users with labels are retrieved along with the 'email' field processed.
        Preconditions:
          - Labels are assigned to a random subset of user IDs prior to retrieval.
        Assertions:
          - Ensure the resulting dataframe is not empty.
          - Assert that 'email_username', 'email_domain', and 'label' columns are present.
        """
        self.update_labels(self.user_ids)
        selected_fields = ["email"]
        user_ids = random.sample(self.user_ids, min(len(self.user_ids), 5))
        df = self.processor.get_selected_users_with_label(user_ids, selected_fields)
        self.assertFalse(df.empty)
        self.assertTrue(set(['email_username', 'email_domain']).issubset(set(df.columns)))
        self.assertTrue("label" in df.columns)

    def test_get_predicted_spam_users(self):
        """
        Verify that the function returns user IDs predicted as spam with greater than a certain confidence level.
        Preconditions:
          - Users must be predicted by the specified context ID with confidence.
        Assertions:
          - Assert that the returned object is a set, containing user IDs.
        """
        spam_users = self.processor.get_predicted_spam_users(PresetContextID.XGBoost_CountVect_1, confidence_threshold=0.5)
        self.assertIsInstance(spam_users, set)

    def test_update_training_data(self):
        """
        Verify that users are correctly marked as training data.
        Preconditions:
          - DataFrame contains user IDs.
        Assertions:
          - Assert that the number of users marked as training data matches the number of user IDs provided.
        """
        df = pd.DataFrame({"user_id": self.user_ids})
        self.processor.update_training_data(df)
        updated_users = UserSpamStatus.objects.filter(is_training_data=True).count()
        self.assertEqual(updated_users, len(self.user_ids))

    def test_save_predictions(self):
        """
        Verify that prediction entries are correctly saved with the appropriate timestamp and model name.
        Preconditions:
          - DataFrame containing 'user_id', 'predictions', and 'confidences'.
        Assertions:
          - Assert that the count of saved predictions matches the number of user IDs.
        """
        prediction_df = pd.DataFrame({"user_id": self.user_ids, "predictions": [True] * len(self.user_ids), "confidences": [0.8] * len(self.user_ids)})
        self.processor.save_predictions(prediction_df, PresetContextID.XGBoost_CountVect_1)
        saved_predictions = UserSpamPrediction.objects.filter(context_id=PresetContextID.XGBoost_CountVect_1.name).count()
        self.assertEqual(saved_predictions, len(self.user_ids))

    # ================= Tests for XGBoostClassifier =================
    def test_xgboost_train_predict_evaluate(self):
        """
        Test the full cycle of training, predicting, and evaluating using the XGBoost classifier.
        Preconditions:
          - Use a mock binary dataset for training and testing.
          - Use CountVectEncoder for feature encoding.
        Assertions:
          - Confirm that the trained model is an instance of XGBClassifier.
          - Ensure that the predictions return a dataframe and contain the correct user IDs.
          - Validate that evaluation metrics returned are correct and include expected keys.
        """
        context_id = "XGBoost_mock"
        classifier = XGBoostClassifier(context_id)
        
        (
            train_feats,
            test_feats,
            train_labels,
            test_labels,
        ) = self.get_mock_binary_dataset()

        encoder = CountVectEncoder(context_id)
        train_feats['user_id'] = train_feats.index
        train_feats = encoder.concatenate(train_feats)
        model = classifier.train(train_feats, train_labels)
        self.assertIsInstance(model, XGBClassifier)

        test_feats['user_id'] = test_feats.index
        test_feats = encoder.concatenate(test_feats)
        prediction_df = classifier.predict(model, test_feats)
        self.assertIsInstance(prediction_df, pd.DataFrame)
        self.assertTrue(set(prediction_df['user_id']) == set(test_feats['user_id']))

        metrics = classifier.evaluate(model, test_feats, test_labels)
        self.assertIsInstance(metrics, dict)
        self.assertTrue(set(metrics.keys()) == {'Accuracy', 'Precision', 'Recall', 'F1', 'test_user_ids'})


    def test_xgboost_save_load(self):
        """
        Test the saving and loading functionality of the XGBoost model.
        Preconditions:
          - A model is trained using a mock binary dataset.
        Assertions:
          - Ensure that the loaded model is an instance of XGBClassifier.
        """
        context_id = "XGBoost_mock"
        classifier = XGBoostClassifier(context_id)
        encoder = CountVectEncoder(context_id)
        (
            train_feats,
            test_feats,
            train_labels,
            test_labels,
        ) = self.get_mock_binary_dataset()

        # Train mock classifier
        train_feats['user_id'] = train_feats.index
        train_feats = encoder.concatenate(train_feats)
        model = classifier.train(train_feats, train_labels)

        # Save and load classifier
        classifier.save(model)
        saved_model = classifier.load()
        self.assertIsInstance(saved_model, XGBClassifier)


    def test_xgboost_save_load_metrics(self):
        """
        Test the saving and loading functionality for the XGBoost evaluation metrics.
        Preconditions:
          - A model is trained and evaluated to generate metrics.
        Assertions:
          - Ensure the loaded metrics are a dictionary containing the expected evaluation metrics.
        """
        context_id = "XGBoost_mock"
        classifier = XGBoostClassifier(context_id)
        encoder = CountVectEncoder(context_id)

        (
            train_feats,
            test_feats,
            train_labels,
            test_labels,
        ) = self.get_mock_binary_dataset()

        # Train mock classifier and compute metrics
        train_feats['user_id'] = train_feats.index
        train_feats = encoder.concatenate(train_feats)
        model = classifier.train(train_feats, train_labels)

        test_feats['user_id'] = test_feats.index
        test_feats = encoder.concatenate(test_feats)
        metrics = classifier.evaluate(model, test_feats, test_labels)

        # Save and load metrics
        classifier.save_metrics(metrics)
        metrics = classifier.load_metrics()
        self.assertIsInstance(metrics, dict)

    # ================= Tests for CountVectEncoder =================
    def test_countvect_encode(self):
        """
        Test the encoding process of the CountVectEncoder.
        Preconditions:
          - Use a mock text dataset.
        Assertions:
          - Ensure that the encoded features dataframe contains the 'input_data' column.
        """
        context_id = "CountVect_mock"
        encoder = CountVectEncoder(context_id)
        feats, labels = self.get_mock_text_dataset(split=False)
        feats['user_id'] = feats.index
        encoded_feats = encoder.encode(feats)
        self.assertIsInstance(encoded_feats, pd.DataFrame)
        self.assertTrue('input_data' in encoded_feats.columns)

    def test_countvect_set_char_analysis_fields(self):
        """
        Test setting character analysis fields in the CountVectEncoder.
        Preconditions:
          - Set specific fields to be analyzed by character.
        Assertions:
          - Ensure the character analysis fields are set correctly.
        """
        context_id = "CountVect_mock"
        encoder = CountVectEncoder(context_id)
        encoder.set_char_analysis_fields(['first_name', 'last_name'])
        self.assertTrue(encoder.char_analysis_fields == ['first_name', 'last_name'])

    # ================= Tests for CategoricalFieldEncoder =================    
    def test_categorical_encode(self):
        """
        Test the encoding process of the CategoricalFieldEncoder.
        Preconditions:
          - Use a mock binary dataset and set categorical fields for encoding.
        Assertions:
          - Check if all categorical fields are converted and if the resulting dataframe is valid.
        """
        encoder = CategoricalFieldEncoder()
        encoder.set_categorical_fields(['target'])
        feats, labels = self.get_mock_binary_dataset(split=False)
        encoded_feats = encoder.encode(labels)
        self.assertIsInstance(encoded_feats, pd.DataFrame)
        # check if all categorical fields are converted

    def test_categorical_set_categorical_fields(self):
        """
        Test setting categorical fields in the CategoricalFieldEncoder.
        Preconditions:
          - Set specific fields to be treated as categorical.
        Assertions:
          - Ensure the categorical fields are set correctly.
        """
        encoder = CategoricalFieldEncoder()
        encoder.set_categorical_fields(['is_active', 'label'])
        self.assertTrue(encoder.categorical_fields == ['is_active', 'label'])

    # ================= Tests for SpamDetectionContext =================
    def test_context_set_classifier(self):
        """
        Test setting a classifier in the SpamDetectionContext.
        Preconditions:
          - Create a spam detection context and instantiate a classifier.
        Assertions:
          - Confirm that the classifier is set correctly in the context.
        """
        context_id = PresetContextID.XGBoost_CountVect_1
        context = SpamDetectionContext(context_id)
        classifier = XGBoostClassifier(context_id.name)
        context.set_classifier(classifier)
        self.assertEqual(context.classifier, classifier)

    def test_context_set_encoder(self):
        """
        Test setting an encoder in the SpamDetectionContext.
        Preconditions:
          - Create a spam detection context and instantiate an encoder.
        Assertions:
          - Confirm that the encoder is set correctly in the context.
        """
        context_id = PresetContextID.XGBoost_CountVect_1
        context = SpamDetectionContext(context_id)
        encoder = CountVectEncoder(context_id.name)
        context.set_encoder(encoder)
        self.assertEqual(context.encoder, encoder)

    def test_context_set_fields(self):
        """
        Test setting fields in the SpamDetectionContext.
        Preconditions:
          - Specify fields to be included in spam detection processing.
        Assertions:
          - Ensure the fields are set correctly within the context.
        """
        context_id = PresetContextID.XGBoost_CountVect_1
        context = SpamDetectionContext(context_id)
        fields = ['email', 'affiliations', 'bio']
        context.set_fields(fields)
        self.assertEqual(context.selected_fields, fields)
