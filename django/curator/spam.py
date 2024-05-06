import logging
from enum import Enum
from typing import List

from .spam_processor import UserSpamStatusProcessor
from . import spam_classifiers
from .spam_classifiers import (
    SpamClassifier,
    Encoder,
    CategoricalFieldEncoder,
    XGBoostClassifier,
    CountVectEncoder,
)
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)
logging.captureWarnings(True)
processor = UserSpamStatusProcessor()


class PresetContextID(Enum):
    """
    Enum for defining preset configurations for spam detection contexts, which include different combinations
    of classifiers and encoders along with specified fields.
    """

    XGBoost_CountVect_1 = "XGBoostClassifier CountVectEncoder PresetFields1"
    XGBoost_CountVect_2 = "XGBoostClassifier CountVectEncoder PresetFields2"
    XGBoost_CountVect_3 = "XGBoostClassifier CountVectEncoder PresetFields3"
    XGBoost_Bert_1 = "XGBoostClassifier BertEncoder PresetFields1"
    NNet_CountVect_1 = "NNetClassifier CountVectEncoder PresetFields1"
    NNet_Bert_1 = "NNetClassifier BertEncoder PresetFields1"
    NaiveBayes_CountVect_1 = "NaiveBayesClassifier CountVectEncoder PresetFields1"
    NaiveBayes_Bert_1 = "NaiveBayesClassifier BertEncoder PresetFields1"

    @classmethod
    def fields(cls, context_id_value: str):
        """
        Determines fields to be included in the dataset based on the context ID value.

        Params:
            context_id_value (str): A value of the context ID indicating the specific preset fields.

        Returns:
            List[str]: A list of field names included in the specified preset.
        """
        field_list = ["email", "affiliations", "bio"]
        if "PresetFields2" in context_id_value:
            field_list.append("is_active")
        elif "PresetFields3" in context_id_value:
            field_list.extend(["personal_url", "professional_url"])
        return field_list

    @classmethod
    def choices(cls):
        """
        Provides the available choices of context IDs.

        Returns:
            tuple: A tuple of tuples, each containing the context ID value and its name.
        """
        print(tuple((i.value, i.name) for i in cls))
        return tuple((i.value, i.name) for i in cls)


class SpamDetectionContext:
    """
    Manages the spam detection process, including setting up classifiers, encoders, and handling data.
    """

    def __init__(self, contex_id: PresetContextID):
        """
        Initializes a spam detection context with a specified context configuration.

        Params:
            context_id (PresetContextID): The context ID from PresetContextID enum defining the configuration.
        """
        self.contex_id = contex_id
        self.classifier: SpamClassifier = None
        self.encoder: Encoder = None
        self.categorical_encoder = CategoricalFieldEncoder()
        self.selected_fields = []
        self.selected_categorical_fields = []

    def set_classifier(self, classifier: SpamClassifier):
        """
        Sets the classifier for the spam detection.

        Params:
            classifier (SpamClassifier): The classifier to be used.
        """
        self.classifier = classifier

    def set_encoder(self, encoder: Encoder):
        """
        Sets the encoder for processing the features.

        Params:
            encoder (Encoder): The encoder to be used.
        """
        self.encoder = encoder

    def set_fields(self, fields: List[str]):
        """
        Sets the fields to be considered for spam detection.

        Params:
            fields (List[str]): A list of field names to be processed.
        """
        self.selected_fields = fields
        self.selected_categorical_fields = [
            field
            for field in self.selected_fields
            if field in processor.field_type["categorical"]
        ]

    def get_model_metrics(self) -> dict:
        """
        Retrieves the metrics of the trained model.

        Returns:
            dict: A dictionary containing the metrics of the model.
        """
        metrics = self.classifier.load_metrics()
        metrics.pop("test_user_ids")
        return metrics

    def train(self, user_ids: List[int] = None):
        """
        Trains the model using the specified user data.

        Params:
            user_ids (List[int], optional): Specific user IDs to include in the training set. If None, use all applicable users.
        """
        if not user_ids:
            df = processor.get_all_users_with_label(self.selected_fields)
        else:
            df = processor.get_selected_users_with_label(user_ids, self.selected_fields)

        self.categorical_encoder.set_categorical_fields(
            self.selected_categorical_fields
        )
        df = self.categorical_encoder.encode(df)

        labels = df["label"]
        feats = df.drop("label", axis=1)
        feats = self.encoder.encode(feats)

        (
            train_feats,
            test_feats,
            train_labels,
            test_labels,
        ) = train_test_split(feats, labels, test_size=0.1, random_state=434)

        model = self.classifier.train(train_feats, train_labels)
        processor.update_training_data(train_feats["user_id"])
        model_metrics = self.classifier.evaluate(model, test_feats, test_labels)
        self.classifier.save(model)
        self.classifier.save_metrics(model_metrics)

    def predict(self, user_ids: List[int] = None):
        """
        Predicts spam status for specified users.

        Params:
            user_ids (List[int], optional): Specific user IDs for which to predict spam status. If None, predict for all users.
        """
        if not user_ids:
            df = processor.get_all_users(self.selected_fields)
        else:
            df = processor.get_selected_users(
                user_ids, self.selected_fields
            )  # TODO check

        self.categorical_encoder.set_categorical_fields(
            self.selected_categorical_fields
        )
        df = self.categorical_encoder.encode(df)

        feats = self.encoder.encode(df)

        model = self.classifier.load()
        result_df = self.classifier.predict(model, feats)
        processor.save_predictions(result_df, self.contex_id)


class SpamDetectionContextFactory:
    """
    Factory class to generate SpamDetectionContext instances with predefined configurations.
    """

    @classmethod
    def create(
        cls, context_id=PresetContextID.XGBoost_CountVect_1
    ) -> SpamDetectionContext:
        """
        Creates a spam detection context based on the specified context ID.

        Params:
            context_id (PresetContextID): The context ID for which to create the spam detection context.

        Returns:
            SpamDetectionContext: The newly created spam detection context.
        """
        spam_detection_contex = SpamDetectionContext(context_id)
        context_id_value = context_id.value.split()

        classifier_class_ = getattr(spam_classifiers, context_id_value[0])
        selected_classifier = classifier_class_(context_id.name)
        spam_detection_contex.set_classifier(selected_classifier)

        encoder_class_ = getattr(spam_classifiers, context_id_value[1])
        selected_encoder = encoder_class_(context_id.name)
        spam_detection_contex.set_encoder(selected_encoder)

        selected_fields = PresetContextID.fields(context_id.value)
        spam_detection_contex.set_fields(selected_fields)

        return spam_detection_contex
