from abc import ABC, abstractmethod
import json
import pickle
import logging
from typing import List
import numpy as np
from pandas import DataFrame

from django.conf import settings

# from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)
SPAM_DIR_PATH = settings.SPAM_DIR_PATH


class SpamClassifier(ABC):
    """
    This class serves as a template for spam classifier variants
    """

    @abstractmethod
    def train(self, train_feats, train_labels) -> object:  # return model object
        pass

    @abstractmethod
    def predict(self, model, feats, confidence_threshold=0.5) -> DataFrame:
        pass

    @abstractmethod
    def evaluate(self, model, test_feats, test_labels) -> dict:
        pass

    @abstractmethod
    def load(
        self,
    ) -> object:  # return model object # TODO: include this into prediction()?
        pass

    @abstractmethod
    def save(self, model):  # TODO: include this into train()?
        pass

    @abstractmethod
    def load_metrics(self):  # TODO: include this into prediction()?
        pass

    @abstractmethod
    def save_metrics(self, model_metrics: dict):  # TODO: include this into train()?
        pass


class Encoder(ABC):
    """
    This class serves as a template for encoder variants
    """

    @abstractmethod
    def encode(self, feats: DataFrame) -> DataFrame:
        """
        TODO:
        """
        pass


class XGBoostClassifier(SpamClassifier):
    def __init__(self, context_id: str):
        """
        Initialize an instance of the XGBoostClassifier with a specific context ID.
        This method sets up the model directory based on the context ID and prepares paths
        for storing the classifier model and metrics.

        Params:
            context_id (str): A unique identifier for the context, used to create dedicated model storage.
        Returns:
            None
        """
        self.context_id = context_id
        self.model_folder = SPAM_DIR_PATH / context_id
        self.model_folder.mkdir(parents=True, exist_ok=True)
        self.classifier_path = self.model_folder / "model.pkl"
        self.metrics_path = self.model_folder / "metrics.json"

    def train(self, train_feats, train_labels):
        """
        Train the XGBoost classifier using the provided features and labels.
        This method fits the XGBoost model to the training data.

        Params:
            train_feats (DataFrame): The input features for training the model.
                                     Only contains columns named "input_data" and "user_id."
            train_labels (Series): The corresponding labels for the training data.
        Returns:
            model (XGBClassifier): The trained XGBoost model.
        """
        logger.info("Training XGBoost classifier....")
        model = XGBClassifier()
        model.fit(np.array(train_feats["input_data"].tolist()), train_labels.tolist())
        return model

    def predict(self, model: XGBClassifier, feats, confidence_threshold=0.5):
        """
        Make predictions using the trained XGBoost model based on the provided features.
        Predictions are made based on a confidence threshold.

        Params:
            model (XGBClassifier): The trained XGBoost model to use for predictions.
                                   Only contains columns named "input_data" and "user_id."
            feats (DataFrame): The features on which predictions are to be made.
            confidence_threshold (float): The threshold to decide between classes (default is 0.5).
        Returns:
            result_df (DataFrame): A DataFrame containing user IDs, predicted confidences, and predictions.
        """
        logger.info("Predicting with XGBoost classifier....")
        probas = model.predict_proba(
            np.array(feats["input_data"].tolist())
        )  # predict_proba() outputs a list of list in the format with [(probability of 0(ham)), (probability of 1(spam))]
        probas = [value[1] for value in probas]
        preds = [int(p >= confidence_threshold) for p in probas]
        # preds = [round(value) for value in confidences]
        result = {
            "user_id": feats["user_id"].tolist(),
            "confidences": probas,
            "predictions": preds,
        }
        result_df = DataFrame(result).replace(np.nan, None)
        return result_df

    def evaluate(self, model: XGBClassifier, test_feats, test_labels):
        """
        Evaluate the XGBoost model using test features and labels.
        Calculates and logs metrics like accuracy, precision, recall, and F1 score.

        Params:
            model (XGBClassifier): The trained model to evaluate.
            test_feats (DataFrame): The features of the test dataset.
                                    Only contains columns named "input_data" and "user_id."
            test_labels (Series): The corresponding labels of the test dataset.
        Returns:
            model_metrics (dict): A dictionary containing evaluation metrics.
        """
        logger.info("Evaluating XGBoost classifier....")
        result = self.predict(model, test_feats)
        accuracy = round(accuracy_score(test_labels, result["predictions"]), 3)
        precision = round(precision_score(test_labels, result["predictions"]), 3)
        recall = round(recall_score(test_labels, result["predictions"]), 3)
        f1 = round(f1_score(test_labels, result["predictions"]), 3)
        logger.info(
            "Evaluation Results: Accuracy={0}, Precision={1}, Recall={2}, F1={3}".format(
                accuracy, precision, recall, f1
            )
        )
        model_metrics = {
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "test_user_ids": test_feats["user_id"].tolist(),
        }
        return model_metrics

    def load(self) -> XGBClassifier:
        """
        Load a previously saved XGBClassifier model from the disk.

        Returns:
            model (XGBClassifier): The loaded model instance.
        """
        logger.info("Loading XGBoost instance....")
        try:
            file = open(self.classifier_path, "rb")
            with file:
                model = pickle.load(file)
                return model
        except OSError:
            logger.info("Could not open/read file: {0}".format(self.classifier_path))

    def save(self, model: XGBClassifier):
        """
        Save the trained XGBClassifier model to disk.

        Params:
            model (XGBClassifier): The model instance to be saved.
        Returns:
            None
        """
        logger.info("Saving XGBoost instance at {0}....".format(self.classifier_path))
        self.model_folder.mkdir(parents=True, exist_ok=True)
        with open(self.classifier_path, "wb") as file:
            pickle.dump(model, file)

    # TODO ask: have save_metrics and load_metrics? or only save()
    def load_metrics(self) -> dict:
        """
        Load model evaluation metrics from a previously saved JSON file.

        Returns:
            model_metrics (dict): A dictionary containing loaded model metrics.
        """
        logger.info("Loading XGBoost model metrics....")
        try:
            file = open(self.metrics_path, "r")
            with file:
                model_metrics = json.load(file)
                return model_metrics

        except OSError:
            logger.info("Could not open/read file:{0}".format(self.metrics_path))

    def save_metrics(self, model_metrics: dict):
        """
        Save the evaluation metrics of the XGBoost model to a JSON file.

        Params:
            model_metrics (dict): The evaluation metrics to save.
        Returns:
            None
        """
        logger.info("Saving XGBoost model metrics at {0}....".format(self.metrics_path))
        with open(self.metrics_path, "w") as file:
            json.dump(model_metrics, file, indent=4)


class CategoricalFieldEncoder(Encoder):
    def __init__(self):
        """
        Initialize the CategoricalFieldEncoder instance. This constructor creates
        an empty list to store names of the fields that will be encoded categorically.

        Returns:
            None
        """
        self.categorical_fields = []

    def set_categorical_fields(self, categorical_fields: List[str]):
        """
        Set the fields that need to be encoded categorically. This method updates
        the list of categorical fields for the encoder.

        Params:
            categorical_fields (List[str]): A list of field names that are to be treated as categorical.
        Returns:
            None
        """
        self.categorical_fields = categorical_fields

    def encode(self, feats: DataFrame) -> DataFrame:
        """
        Encode the specified categorical fields in the provided DataFrame.
        This method applies label encoding to the columns specified in the categorical_fields list.

        Params:
            feats (DataFrame): The DataFrame containing the data to be encoded.
                               Contains columns converted from the selected fields.
        Returns:
            feats (DataFrame): The DataFrame with the categorical fields encoded.
                               Contains columns converted from the selected fields.
        """
        for col in self.categorical_fields:
            le = LabelEncoder()
            feats[col] = le.fit_transform(feats[col].tolist())
        return feats


class CountVectEncoder(Encoder):
    def __init__(self, context_id: str):
        """
        Initialize the CountVectEncoder instance with a specific context ID. This sets up
        the model directory and prepares the path for storing the encoder.

        Params:
            context_id (str): A unique identifier for the context, used to create dedicated encoder storage.
        Returns:
            None
        """
        self.context_id = context_id
        self.model_folder = SPAM_DIR_PATH / context_id
        self.model_folder.mkdir(parents=True, exist_ok=True)
        self.encoder_path = self.model_folder / "encoder.pkl"
        self.char_analysis_fields = [
            "first_name",
            "last_name",
            "email_username",
            "email_domain",
        ]

    def set_char_analysis_fields(self, char_analysis_fields):
        """
        Set the fields that require character-level analysis. This method updates the list of
        fields to be analyzed at the character level.

        Params:
            char_analysis_fields: A list of field names for character-level analysis.
        Returns:
            None
        """
        self.char_analysis_fields = char_analysis_fields

    def encode(self, feats: DataFrame) -> DataFrame:
        """
        Encode the specified fields in the provided DataFrame using CountVectorizer.
        This method manages the loading or creation of CountVectorizers for each field and
        encodes the data accordingly.

        Params:
            feats (DataFrame): The DataFrame containing the data to be encoded.
                               Contains columns converted from the selected fields.
        Returns:
            DataFrame: A DataFrame with the encoded data.
                       Only contains columns named "input_data" and "user_id."
        """

        def get_encoded_sequences(data: list, vectorizer: CountVectorizer):
            return list(np.array(vectorizer.transform(data).todense()))

        # load or fit CountVectorizer
        encoders_dict = self.__load()
        if not encoders_dict:
            logger.info("No encoder instances found. Creating new encoder....")
            encoders_dict = self.__fit(feats)
            self.__save(encoders_dict)

        encoded_df = DataFrame(columns=feats.columns, index=feats.index)
        for col in feats.columns:
            if feats[col].dtype == np.int64 or feats[col].dtype == int:
                encoded_df[col] = feats[col]
                continue

            vectorized_seqs = get_encoded_sequences(feats[col], encoders_dict[col])
            encoded_df[col] = DataFrame(
                {col: vectorized_seqs}, columns=[col], index=feats.index
            )
        return self.concatenate(encoded_df)

    def __fit(self, feats: DataFrame):
        """
        Fit CountVectorizer for each field specified in the DataFrame that is not of integer type.

        Params:
            feats (DataFrame): The DataFrame containing the data for which to fit the vectorizers.
        Returns:
            dict: A dictionary of CountVectorizer instances for each field.
        """

        def fit_vectorizer(data, analyzer="word", ngram_range=(1, 1)):
            return CountVectorizer(analyzer=analyzer, ngram_range=ngram_range).fit(data)

        encoders_dict = {}
        # print(feats.dtypes)
        # print(feats.head())
        for col in feats.columns:
            data_list = feats[col].tolist()
            if feats[col].dtype == np.int64 or feats[col].dtype == int:
                continue
            if col in self.char_analysis_fields:
                vectorizer = fit_vectorizer(
                    data_list, analyzer="char", ngram_range=(1, 1)
                )
            else:
                vectorizer = fit_vectorizer(data_list)
            encoders_dict[col] = vectorizer
        return encoders_dict

    def __load(self):
        """
        Load the CountVectorizer instances from the encoder path if they exist.

        Returns:
            dict: A dictionary containing the loaded CountVectorizer instances, or None if loading fails.
        """
        try:
            file = open(self.encoder_path, "rb")
            with file:
                encoders_dict = pickle.load(file)
                return encoders_dict
        except OSError:
            logger.info("Could not open/read file:{0}".format(self.encoder_path))

    def __save(self, encoders_dict: dict):
        """
        Save the dictionary of CountVectorizer instances to disk.

        Params:
            encoders_dict (dict): The dictionary of CountVectorizer instances to be saved.
        Returns:
            None
        """
        self.model_folder.mkdir(parents=True, exist_ok=True)
        with open(self.encoder_path, "wb") as file:
            pickle.dump(encoders_dict, file)

    def concatenate(self, encoded_df: DataFrame):
        """
        Concatenate tokenized data for each record in the DataFrame to create a unified
        'input_data' field alongside 'user_id'.

        Params:
            encoded_df (DataFrame): The DataFrame containing tokenized data to be concatenated.
        Returns:
            DataFrame: A DataFrame with concatenated tokenized data and 'user_id' field.
        """
        columnlist = [
            col
            for col in encoded_df.columns
            if col != "user_id" and col != "input_data"
        ]

        def concatinate_tokenized_data(row):
            input_data = []
            for col in columnlist:
                if isinstance(row[col], np.ndarray):
                    input_data = input_data + row[col].tolist()
                else:
                    input_data.append(row[col])
            return input_data

        encoded_df["input_data"] = encoded_df.apply(concatinate_tokenized_data, axis=1)
        return encoded_df[
            ["user_id", "input_data"]
        ]  # dataframe with columns ['user_id', 'input_data']
