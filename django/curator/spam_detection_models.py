import re
import os.path
import pickle
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

        # TODO if pickle files exist, skip this part
        self.user_meta_classifier_metrics = self.user_meta_classifier.fit()
        self.text_classifier.fit()
        # self.text_classifier_metrics = self.text_classifier.fit() TODO make text_classifier return matrics
        self.text_classifier_metrics = {}

    def execute(self):  # API for ML functions
        """
        1. if there are some users that have None in all labelled_by_curator, labelled_by_user_classifier,
            and labelled_by_text_classifier, predict() should be called.

            - make sure model exitsts, call predict().
               The function will save its results to the DB.
                - BioSpamClassifier.predict()
                - UserMetadataSpamClassifier.predict()

        2. filtering the DB, return the list of all user_id (and user name) with a certain confidence level
                return UserPipeline.get_spam_users()
                    ... this functions will first filter out the users with labelled_by_curator==True,
                        but the ones with None, only get users with labelled_by_user_classifier == True
                        or labelled_by_text_classifier == True with a specific confidence level
        """
        # TODO check DB for users with None in all labelled_by_curator, labelled_by_user_classifier, and labelled_by_text_classifier,
        self.user_meta_classifier.predict()
        self.text_classifier.predict()

        # Return user_ids and metrics of the model
        return (
            self.processor.get_spam_users(),
            self.user_meta_classifier_metrics,
            self.text_classifier_metrics,
        )

    def refine(self):
        # TODO: use the newly updated labelled_by_user_classifier and call partial_train()?
        self.user_meta_classifier_metrics = self.user_meta_classifier.partial_fit()
        self.text_classifier.fit()
        # self.text_classifier_metrics = self.text_classifier.fit() TODO make text_classifier return matrics
        return self.user_meta_classifier_metrics, self.text_classifier_metrics


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

    # @abstractmethod
    # def get_validation_metrics(self): #TODO save metrics as json or pickle
    #     pass


class TextSpamClassifier(SpamClassifier):
    # This is temporary until we find a better solution.
    # We are saving and loading models straight to the VM,
    # ideally, we instead store it in some object storage instead.
    INITIAL_FILE_PATH = "curator/label.json"
    MODEL_FILE_PATH = "curator/instance.pkl"

    def load_model():
        if os.path.isfile(TextSpamClassifier.MODEL_FILE_PATH):
            TextSpamClassifier.fit()
        with open(TextSpamClassifier.MODEL_FILE_PATH, "rb") as file:
            return pickle.load(file)

    def save_model(model):
        with open(TextSpamClassifier.MODEL_FILE_PATH, "wb") as file:
            pickle.dump(model, file)

    def fit(self):
        # TODO:
        model = Pipeline(
            [
                ("cleaner", FunctionTransformer(TextSpamClassifier.preprocess)),
                ("countvectorizer", CountVectorizer(lowercase=True)),
                ("classifier", MultinomialNB()),
            ]
        )

        untrained_df = self.processor.get_untrained_df()

        if untrained_df.empty == False:
            bio = untrained_df[["bio", "labelled_by_curator"]][
                untrained_df["bio"] != ""
            ]
            research_interests = untrained_df[
                ["research_interests", "labelled_by_curator"]
            ][untrained_df["research_interests"] != ""]

            train_x = pd.concat(
                [bio["bio"], research_interests["research_interests"]]
            ).to_list()

            train_y = pd.concat(
                [bio["labelled_by_curator"], research_interests["labelled_by_curator"]]
            )

            model.fit(train_x, train_y)

        TextSpamClassifier.save_model(model)
        # TODO return metrics

    def predict(self):
        all_users_df = self.processor.get_all_users_df()
        model = TextSpamClassifier.load_model()

    def preprocess(text_list: List[str]):
        text_list = [
            TextSpamClassifier.__text_cleanup_pipeline(text) for text in text_list
        ]
        return text_list

    def __text_cleanup_pipeline(text: str):
        text = str(text)
        text = TextSpamClassifier.__convert_text_to_lowercase(text)
        text = TextSpamClassifier.__replace_urls_with_webtag(text)
        text = TextSpamClassifier.__replace_numbers_with_zero(text)
        text = TextSpamClassifier.__remove_markdown(text)
        text = TextSpamClassifier.__remove_excess_spaces(text)
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
    TOKENIZER_FILE_PATH = "tokenizer.pkl"
    MODEL_FILE_PATH = "spam_xgb_classifier.pkl"

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
        ) = self.__preprocess_for_training(
            df
        )  # preprocess

        test_prediction, metrics, model = self.__train_xgboost_classifer(
            train_matrix, test_matrix, train_target, test_target
        )  # train

        pickle.dump(model, open(self.MODEL_FILE_PATH, "wb"))  # save model

        self.processor.update_training_data(df)  # save last trained date
        return metrics  # if needed

    def partial_fit(self):
        # obtain df from pipleline
        df = self.processor.get_untrained_df()
        if df.empty == True:
            return  # if no untrained data found

        model = pickle.load(open(self.MODEL_FILE_PATH, "rb"))  # load model

        (
            train_matrix,
            test_matrix,
            train_target,
            test_target,
        ) = self.__preprocess_for_training(
            df
        )  # preprocess

        test_prediction, metrics, model = self.__partial_train_xgboost_classifer(
            train_matrix, test_matrix, train_target, test_target, model
        )  # partial train

        pickle.dump(model, open(self.MODEL_FILE_PATH, "wb"))  # save model

        self.processor.update_training_data(df)  # save last trained date
        return metrics  # if needed

    def predict(self):
        df = self.processor.get_unlabelled_by_curator_df()
        if df.empty:  # no-op if no data found
            return

        feat_matrix, _ = self.__preprocess_for_prediction(df)  # preprocess

        model = pickle.load(open(self.MODEL_FILE_PATH, "rb"))  # load model

        predictions, confidences = self.__predict_xgboost_classifer(
            model, feat_matrix
        )  # predict
        df["labelled_by_user_classifier"] = predictions
        df["user_classifier_confidence"] = confidences
        df = df.filter(
            ["user_id", "user_classifier_confidence", "labelled_by_user_classifier"],
            axis=1,
        ).replace(np.nan, None)
        self.processor.update_predictions(
            df, isTextClassifier=False
        )  # save the results to DB
        # return result_df TODO we don't have to return this, do we?

    def __train_xgboost_classifer(
        self, train_matrix, test_matrix, train_target, test_target
    ):
        # Fit to model
        model = xgb.XGBClassifier()
        model.fit(train_matrix, train_target)

        predictions, metrics = self.__validate_model(model, test_matrix, test_target)
        return predictions, metrics, model

    def __partial_train_xgboost_classifer(
        self,
        train_matrix,
        test_matrix,
        train_target,
        test_target,
        old_model: xgb.XGBClassifier,
    ):
        # Fit the new data to model
        retrained_model = xgb.XGBClassifier()
        retrained_model.fit(
            train_matrix, train_target, xgb_model=old_model.get_booster()
        )
        predictions, metrics = self.__validate_model(
            retrained_model, test_matrix, test_target
        )
        return predictions, metrics, retrained_model

    def __predict_xgboost_classifer(self, model: xgb.XGBClassifier, feat_matrix):
        confidences = model.predict(feat_matrix)
        predictions = [round(value) for value in confidences]
        return predictions, confidences

    def __validate_model(self, model: xgb.XGBClassifier, test_matrix, test_target):
        confidences = model.predict(test_matrix)
        predictions = [round(value) for value in confidences]
        # print("test_target type")
        # test_target = test_target.to_numpy()
        # y_df = pd.DataFrame(test_target)
        # pred_df = pd.DataFrame(predictions)
        # y_df.to_csv("test_target.csv")
        # pred_df.to_csv("predictions.csv")
        # uni, cnt = np.unique(test_target, return_counts=True)
        # print(dict(zip(uni, cnt)))
        # uni, cnt = np.unique(predictions, return_counts=True)
        # print(dict(zip(uni, cnt)))
        # print(type(test_target[0]))
        # print(type(predictions[0]))

        # calculate metrics
        # TODO debug for "ValueError: Classification metrics can't handle a mix of unknown and binary targets"
        # accuracy = accuracy_score(test_target, predictions)
        # precision = precision_score(test_target, predictions)
        # recall = recall_score(test_target, predictions)
        # f1 = f1_score(test_target, predictions)
        # model_metrics = (accuracy, precision, recall, f1)
        model_metrics = ""
        return predictions, model_metrics

    def __preprocess_for_training(self, df: pd.DataFrame):
        df = self.__input_df_transformation(df)
        target = df["labelled_by_curator"]
        feat_matrix = df.drop(["labelled_by_curator"], axis=1)
        (
            training_matrix,
            validation_matrix,
            training_target,
            validation_target,
        ) = train_test_split(
            feat_matrix, target, test_size=0.1, random_state=434
        )  # TODO save whch user_id was used for training

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
        return training_input, validation_input, training_target, validation_target

    def __preprocess_for_prediction(self, df: pd.DataFrame):
        df = self.__input_df_transformation(df)
        target = df["labelled_by_curator"]
        feat_matrix = df.drop(["labelled_by_curator"], axis=1)

        # Apply Tokenizer to the feature matrix to be predicted
        tokenized_matrix_dict = self.__apply_tokenizer(feat_matrix)
        model_input = self.__get_model_input(feat_matrix, tokenized_matrix_dict)
        return model_input, target

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
