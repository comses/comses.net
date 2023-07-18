import re
import os.path
import pickle
import json
from ast import literal_eval

import pandas as pd
import numpy as np
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb

from curator.spam import UserSpamStatusProcessor
from curator.models import UserSpamStatus
from typing import List

from abc import ABC, abstractmethod


class SpamDetection:
    def __init__(self):
        """
        if no model pickle files found, execute fit()
            - if all users have None in labelled_by_curator, load to DB by calling Pipeline.update_labels()
            - additionally, if no labels file, throw exception
        """
        self.processor = UserSpamStatusProcessor()
        self.user_meta_classifier = UserMetadataSpamClassifier()
        self.text_classifier = TextSpamClassifier()
        self.processor.update_labels(check_DB=True)

        # Check whether UserMetadataSpamClassifier model file exists
        if os.path.exists(self.user_meta_classifier.MODEL_METRICS_FILE_PATH):
            with open(self.user_meta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
                self.user_meta_classifier_metrics = json.load(json_file)
        else:
            self.user_meta_classifier_metrics = self.user_meta_classifier.fit()

        # TODO: remove commnet out after TextSpamClassifier() is fixed
        # Check whether TextSpamClassifier model file exists
        # if os.path.exists(self.text_classifier.MODEL_METRICS_FILE_PATH):
        #     with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
        #         self.text_classifier_metrics = json.load(json_file)
        # else:
        #     self.text_classifier.fit()
        # self.text_classifier_metrics = self.text_classifier.fit()

        self.text_classifier_metrics = {}
        print("hello!!")

    def execute(self):  # API for ML functions
        # Check DB for unlabelled users (None in all labelled_by_curator, labelled_by_user_classifier, and labelled_by_text_classifier)
        if len(self.processor.get_unlabelled_users()) != 0:
            # if there are some unlabelled users, predict
            self.user_meta_classifier.predict()
            # self.text_classifier.predict() TODO: remove commnet out after TextSpamClassifier() is fixed

        # Return user_ids and metrics of the model
        return (
            self.processor.get_spam_users(),
            self.user_meta_classifier_metrics,
            self.text_classifier_metrics,
        )

    def refine(self):  # Retrain models using new data in DB
        self.user_meta_classifier_metrics = self.user_meta_classifier.partial_fit()
        # self.text_classifier_metrics = self.text_classifier.fit() TODO: remove commnet out after TextSpamClassifier() is fixed
        return self.user_meta_classifier_metrics, self.text_classifier_metrics

    def get_model_metrics(self):
        # We can assume that model and model metrics files exist after __init__
        with open(self.user_meta_classifier.MODEL_METRICS_FILE_PATH) as json_file:
            self.user_meta_classifier_metrics = json.load(json_file)

        # TODO: remove commnet out after TextSpamClassifier() is fixed
        # with open(self.text_classifier.MODEL_METRICS_FILE_PATH) as json_file:
        #     self.text_classifier_metrics = json.load(json_file)

        return {
            "UserMetadataSpamClassifier": self.user_meta_classifier_metrics,
            "TextSpamClassifier": self.text_classifier_metrics,
        }


class SpamClassifier(ABC):
    # This class serves as a template for spam classifer varients
    def __init__(self):
        self.processor = UserSpamStatusProcessor()

    @abstractmethod
    def fit(self):
        pass

    @abstractmethod
    def partial_fit(self):
        # only used in UserClassifier at this point
        pass

    @abstractmethod
    def predict(self):
        # predict only the ones with unlabelled_by_curator == None
        pass

    def get_predictions(self, model, feat_matrix):
        """
        Params : model ... Model instance
                feat_matrix ... List of numerical values, which is an input to the model
        Returns : predictions ... List of predictions made by the model. Consists of 0 (ham) and 1 (spam).
                  confidences ... List of floating values, which represent probabilities whether a user is 1 (spam)
        """
        confidences = model.predict_proba(
            feat_matrix
        )  # predict_proba() outputs a list of list in the format of [(probability of 0(ham)), (probability of 1(spam))]
        confidences = [value[1] for value in confidences]
        predictions = [round(value) for value in confidences]
        return predictions, confidences

    def validate_model(
        self,
        model,
        test_user_ids: list[int],
        test_matrix: list,
        test_target: list[int],
        save_path: str,
    ):
        """
        Params : model ... Model instance
                test_user_ids ... List of user_id which test_matrix, validation input, was taken from
                test_matrix ... List of numerical values, which is an input to the model
                test_target ... List of 0 (ham) and 1 (spam) labelled by curators
                save_path ... String of file path to save the model metrics json file
        Output : json file ... This stores model scores and user_ids used to validate the model. The format is as follows.
                 {"Accuracy": float, "Precision": float, "Recall": float, "F1",float, "test_user_ids": list of user_id}
        Returns : predictions ... List of predictions made by the model. Consists of 0 (ham) and 1 (spam).
                  model_metrics ... Dictionary of the same format as the output json file.
        """
        predictions, _ = self.get_predictions(model, test_matrix)

        print(type(test_user_ids[0]))
        print(type(test_target[0]))
        print("predictions", predictions)
        print("test_target", test_target)
        accuracy = round(accuracy_score(test_target, predictions), 3)
        precision = round(precision_score(test_target, predictions), 3)
        recall = round(recall_score(test_target, predictions), 3)
        f1 = round(f1_score(test_target, predictions), 3)
        model_metrics = {
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "test_user_ids": test_user_ids,
        }

        with open(save_path, "w") as outfile:
            json.dump(model_metrics, outfile, indent=4)

        return predictions, model_metrics


class TextSpamClassifier(SpamClassifier):
    # This is temporary until we find a better solution.
    # We are saving and loading models straight to the VM,
    # ideally, we instead store it in some object storage instead.

    def __init__(self):
        SpamClassifier.__init__(self)
        # self.MODEL_FILE_PATH = "curator/text_classifier.pkl"
        self.MODEL_FILE_PATH = "text_classifier.pkl"  # TODO for test purpose, replace this to "curator/text_classifier.pkl" later
        self.MODEL_METRICS_FILE_PATH = "text_classifier_metrics.json"

    def load_model(self):
        if os.path.isfile(self.MODEL_FILE_PATH):
            self.fit()
        with open(self.MODEL_FILE_PATH, "rb") as file:
            return pickle.load(file)

    def save_model(self, model):
        with open(self.MODEL_FILE_PATH, "wb") as file:
            pickle.dump(model, file)

    def fit(self):
        # TODO:
        model = Pipeline(
            [
                ("cleaner", FunctionTransformer(self.preprocess)),
                ("countvectorizer", CountVectorizer(lowercase=True)),
                ("classifier", MultinomialNB()),
            ]
        )

        untrained_df = self.processor.get_untrained_df()

        if untrained_df.empty:
            return
        data_x, data_y = self.concat_pd(untrained_df)
        (
            train_x,
            test_x,
            train_y,
            test_y,
        ) = train_test_split(data_x, data_y, test_size=0.1, random_state=434)
        model.fit(train_x, train_y)
        self.save_model(model)
        test_predictions, model_metrics = self.validate_model(
            model, test_x, test_y, self.MODEL_METRICS_FILE_PATH
        )
        return model_metrics

    def partial_fit(self):
        """
        Since there is no partial training feature in TextSpamClassifier, this function calls fit() and train based on all data
        """
        self.fit()

    def concat_pd(self, df):
        bio = df[["bio", "labelled_by_curator"]][df["bio"] != ""]
        research_interests = df[["research_interests", "labelled_by_curator"]][
            df["research_interests"] != ""
        ]

        train_x = pd.concat(
            [bio["bio"], research_interests["research_interests"]]
        ).to_list()

        train_y = pd.concat(
            [bio["labelled_by_curator"], research_interests["labelled_by_curator"]]
        )
        return train_x, train_y

    def predict(self):
        df = self.processor.get_unlabelled_by_curator_df()
        if df.empty:  # no-op if no data found
            return

        model = self.load_model()
        concat_pd = self.concat_pd(df)

        predictions, confidences = self.get_predictions(model, concat_pd)

        # save the results to DB
        df["labelled_by_text_classifier"] = predictions
        df["text_classifier_confidence"] = confidences
        df = df.filter(
            ["user_id", "text_classifier_confidence", "labelled_by_text_classifier"],
            axis=1,
        ).replace(np.nan, None)
        self.processor.update_predictions(df, isTextClassifier=True)

    def preprocess(self, text_list: List[str]):
        text_list = [self.__text_cleanup_pipeline(text) for text in text_list]
        return text_list

    def __text_cleanup_pipeline(self, text: str):
        text = str(text)
        text = self.__convert_text_to_lowercase(text)
        text = self.__replace_urls_with_webtag(text)
        text = self.__replace_numbers_with_zero(text)
        text = self.__remove_markdown(text)
        text = self.__remove_excess_spaces(text)
        return text

    def __convert_text_to_lowercase(text: str):
        return text.lower()

    def __replace_urls_with_webtag(text: str):
        return re.sub(r"http\S+|www\S+", " webtag ", text)

    def __replace_numbers_with_zero(text: str):
        return re.sub(r"\d+", " 0 ", text)

    def __remove_markdown(text: str):
        return re.sub(r"<.*?>", " ", text)

    def __remove_excess_spaces(text: str):
        return re.sub(r"\s+", " ", text)


class UserMetadataSpamClassifier(SpamClassifier):
    def __init__(self):
        SpamClassifier.__init__(self)
        self.TOKENIZER_FILE_PATH = "tokenizer.pkl"
        self.MODEL_FILE_PATH = "user_meta_classifier.pkl"
        self.MODEL_METRICS_FILE_PATH = "user_meta_classifier_metrics.json"

    def fit(self):
        # obtain df from pipleline
        df = self.processor.get_untrained_df()
        if df.empty == True:
            return  # if no untrained data found

        (
            train_matrix,
            test_matrix,
            train_target,
            test_target,
            test_user_ids,
        ) = self.__preprocess_for_training(
            df
        )  # preprocess

        test_prediction, metrics, model = self.__train_xgboost_classifer(
            train_matrix, test_matrix, train_target, test_target, test_user_ids
        )  # train

        pickle.dump(model, open(self.MODEL_FILE_PATH, "wb"))  # save model

        self.processor.update_training_data(df)  # save last trained date
        return metrics  # if needed

    def partial_fit(self):
        # obtain df from pipleline
        df = self.processor.get_untrained_df()
        if df.empty == True:
            return  # if no untrained data found

        print("partial_fit in UserMetadataSpamClassifier")
        model = pickle.load(open(self.MODEL_FILE_PATH, "rb"))  # load model

        (
            train_matrix,
            test_matrix,
            train_target,
            test_target,
            test_user_ids,
        ) = self.__preprocess_for_training(
            df
        )  # preprocess

        test_prediction, metrics, model = self.__partial_train_xgboost_classifer(
            train_matrix, test_matrix, train_target, test_target, test_user_ids, model
        )  # partial train

        pickle.dump(model, open(self.MODEL_FILE_PATH, "wb"))  # save model

        # self.processor.update_training_data(df)  # save last trained date
        return metrics

    def predict(self):
        df = self.processor.get_unlabelled_by_curator_df()
        if df.empty:  # no-op if no data found
            return

        feat_matrix = self.__preprocess_for_prediction(df)  # preprocess

        model = pickle.load(open(self.MODEL_FILE_PATH, "rb"))  # load model

        predictions, confidences = self.get_predictions(model, feat_matrix)

        df["labelled_by_user_classifier"] = predictions
        df["user_classifier_confidence"] = confidences
        df = df.filter(
            ["user_id", "user_classifier_confidence", "labelled_by_user_classifier"],
            axis=1,
        ).replace(np.nan, None)
        self.processor.update_predictions(
            df, isTextClassifier=False
        )  # save the results to DB

    def __train_xgboost_classifer(
        self,
        train_matrix: list,
        test_matrix: list,
        train_target: list,
        test_target: list,
        test_user_ids: list,
    ):
        # Fit to model
        model = xgb.XGBClassifier()
        model.fit(train_matrix, train_target)

        predictions, metrics = self.validate_model(
            model, test_user_ids, test_matrix, test_target, self.MODEL_METRICS_FILE_PATH
        )
        return predictions, metrics, model

    def __partial_train_xgboost_classifer(
        self,
        train_matrix: list,
        test_matrix: list,
        train_target: list,
        test_target: list,
        test_user_ids: list,
        old_model: xgb.XGBClassifier,
    ):
        # Fit the new data to model
        retrained_model = xgb.XGBClassifier()
        retrained_model.fit(
            train_matrix, train_target, xgb_model=old_model.get_booster()
        )
        predictions, metrics = self.validate_model(
            retrained_model,
            test_user_ids,
            test_matrix,
            test_target,
            self.MODEL_METRICS_FILE_PATH,
        )
        return predictions, metrics, retrained_model

    # def __predict_xgboost_classifer(self, model: xgb.XGBClassifier, feat_matrix: list):
    #     confidences = model.predict_proba(feat_matrix)
    #     predictions = [round(value[1]) for value in confidences]
    #     return predictions, confidences

    def __preprocess_for_training(self, df: pd.DataFrame):
        df = self.__input_df_transformation(df)
        target = df["labelled_by_curator"].values.tolist()
        feat_matrix = df.drop(["labelled_by_curator"], axis=1)
        (
            training_matrix,
            validation_matrix,
            training_target,
            validation_target,
        ) = train_test_split(feat_matrix, target, test_size=0.1, random_state=434)
        validation_user_ids = validation_matrix["user_id"].values.tolist()

        # Initialize or Update Tokenizer and Apply it to the train feature matrix
        # training_feature_matrix = training_matrix.drop(["user_id"], axis=1)
        tokenizer_dict = {}
        if os.path.exists(self.TOKENIZER_FILE_PATH):
            tokenizer_dict = self.__update_tokenizer(training_matrix)
        else:
            tokenizer_dict = self.__initialize_tokenizer(training_matrix)

        tokenized_matrix_dict = self.__apply_tokenizer(
            training_matrix, tokenizer_dict=tokenizer_dict
        )
        training_input = self.__get_model_input(training_matrix, tokenized_matrix_dict)

        # Apply Tokenizer to the validation feature matrix
        # validation_feature_matrix = validation_matrix.drop(["user_id"], axis=1)
        tokenized_matrix_dict = self.__apply_tokenizer(
            validation_matrix, tokenizer_dict=tokenizer_dict
        )
        validation_input = self.__get_model_input(
            validation_matrix, tokenized_matrix_dict
        )
        return (
            training_input.tolist(),
            validation_input.tolist(),
            training_target,
            validation_target,
            validation_user_ids,
        )

    def __preprocess_for_prediction(self, df: pd.DataFrame):
        df = self.__input_df_transformation(df)
        feat_matrix = df.drop(["labelled_by_curator"], axis=1)

        # Apply Tokenizer to the feature matrix to be predicted
        tokenized_matrix_dict = self.__apply_tokenizer(feat_matrix)
        model_input = self.__get_model_input(feat_matrix, tokenized_matrix_dict)
        return model_input.tolist()

    def __input_df_transformation(self, df: pd.DataFrame):
        # extract relavant columns and reform data of some columns
        if "labelled_by_curator" not in df.columns:
            df["labelled_by_curator"] = 0  # only when mode='predict'
        df = df.filter(
            [
                "user_id",
                "labelled_by_curator",
                "first_name",
                "last_name",
                "is_active",
                "email",
                "affiliations",
                "bio",
            ],
            axis=1,
        )
        df[
            ["first_name", "last_name", "is_active", "email", "affiliations", "bio"]
        ] = df[
            ["first_name", "last_name", "is_active", "email", "affiliations", "bio"]
        ].fillna(
            ""
        )
        df[["user_id", "labelled_by_curator"]] = df[
            ["user_id", "labelled_by_curator"]
        ].fillna(0)
        df["affiliations"] = df.apply(
            lambda row: self.__reform__affiliations(row["affiliations"]), axis=1
        )
        df["is_active"] = df.apply(
            lambda row: self.__reform__is_active(row["is_active"]), axis=1
        )
        return df

    def __reform__affiliations(self, array):
        array = literal_eval(array)
        if len(array) == 0:
            return ""
        affiliations = []
        for affiliation_dict in array:
            name = (
                affiliation_dict["name"]
                if ("name" in affiliation_dict.keys())
                else "NaN"
            )
            url = (
                affiliation_dict["url"] if ("url" in affiliation_dict.keys()) else "NaN"
            )
            ror_id = (
                affiliation_dict["ror_id"]
                if ("ror_id" in affiliation_dict.keys())
                else "NaN"
            )
            affiliation = f"{name} (url: {url}, ror id: {ror_id})"
            affiliations.append(affiliation)
        return ", ".join(affiliations)

    def __reform__is_active(self, val):
        return 1 if val == "t" else 0

    def __get_model_input(self, feat_matrix: pd.DataFrame, tokenized_matrix_dict):
        tokenized_matrix = pd.DataFrame(
            columns=feat_matrix.columns, index=feat_matrix.index
        )
        tokenized_matrix["user_id"] = feat_matrix["user_id"]
        tokenized_matrix["is_active"] = feat_matrix["is_active"]
        del feat_matrix
        for col in tokenized_matrix.columns:
            if col == "is_active" or col == "user_id":
                continue
            tokenized_matrix[col] = tokenized_matrix[col].astype(object)
            temp_df = pd.DataFrame(
                {col: tokenized_matrix_dict[col]},
                columns=[col],
                index=tokenized_matrix.index,
            )
            tokenized_matrix[col] = temp_df
        tokenized_matrix["model_input"] = tokenized_matrix.apply(
            lambda row: self.__concatenate_row(row), axis=1
        )
        return np.array(tokenized_matrix["model_input"].tolist())

    def __concatenate_row(self, row):
        model_input = np.concatenate(
            (
                row["first_name"],
                row["last_name"],
                np.array([row["is_active"]]),
                row["email"],
                row["affiliations"],
                row["bio"],
            )
        )
        return model_input

    def __initialize_tokenizer(self, feat_matrix: pd.DataFrame):
        tokenizer_dict = {}
        for col in feat_matrix.columns:
            if col == "is_active" or col == "user_id":
                continue
            # initialize tokenizer
            tokenizer = Tokenizer(num_words=2000, char_level=True, oov_token="<OOV>")
            tokenizer.fit_on_texts(feat_matrix[col])
            tokenizer_dict[col] = tokenizer
        pickle.dump(tokenizer_dict, open(self.TOKENIZER_FILE_PATH, "wb"))  # update file
        return tokenizer_dict

    def __load_tokenizer(self):
        tokenizer_dict = pickle.load(open(self.TOKENIZER_FILE_PATH, "rb"))
        return tokenizer_dict

    def __update_tokenizer(self, feat_matrix: pd.DataFrame):
        """
        assumes that the tokenizer dictionary has already been pickled to disk and
        loads it into memory before updating it based on the data in feat_matrix
        """
        tokenizer_dict = self.__load_tokenizer()
        for col in feat_matrix.columns:
            if col == "is_active" or col == "user_id":
                continue
            tokenizer = tokenizer_dict[col]
            tokenizer.fit_on_texts(feat_matrix[col])
            tokenizer_dict[col] = tokenizer
        pickle.dump(tokenizer_dict, open(self.TOKENIZER_FILE_PATH, "wb"))  # update file
        return tokenizer_dict

    def __apply_tokenizer(self, feat_matrix: pd.DataFrame, tokenizer_dict=None):
        tokenized_matrix_dict = {}
        if tokenizer_dict == None:
            tokenizer_dict = self.__load_tokenizer()
        for col in feat_matrix.columns:
            if col == "is_active" or col == "user_id":
                continue
            tokenizer = tokenizer_dict[col]
            column_sequences = tokenizer.texts_to_sequences(
                feat_matrix[col]
            )  # tokenize texts
            column_padded = pad_sequences(
                column_sequences, maxlen=800, padding="post", truncating="post"
            )
            tokenized_matrix_dict[col] = list(column_padded)
        return tokenized_matrix_dict
