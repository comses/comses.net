import json
import numpy as np
import os.path
import pandas as pd
import pickle
import re

from abc import ABC, abstractmethod
from ast import literal_eval
from django.conf import settings
from typing import List
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import FunctionTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb

from .spam_processor import UserSpamStatusProcessor


SPAM_DIR_PATH = settings.SPAM_DIR_PATH


class SpamClassifier(ABC):
    # This class serves as a template for spam classifer variants
    def __init__(self):
        self.processor = UserSpamStatusProcessor()

    @abstractmethod
    def fit(self):
        pass

    @abstractmethod
    def predict(self):
        # predict only the ones with unlabelled_by_curator == None
        pass

    def get_predictions(self, model, feat_list: list):
        """
        Params : model ... Model instance
                feat_list ... List of texts
        Returns : predictions ... List of predictions made by the model. Consists of 0 (ham) and 1 (spam).
                  confidences ... List of floating values, which represent probabilities whether a user is 1 (spam)
        """
        confidences = model.predict_proba(
            feat_list
        )  # predict_proba() outputs a list of list in the format of [(probability of 0(ham)), (probability of 1(spam))]
        confidences = [value[1] for value in confidences]
        predictions = [round(value) for value in confidences]
        return predictions, confidences

    def validate_model(
        self,
        model,
        test_user_ids: list,
        test_feats: list,
        test_target: list,
        save_path: str,
    ):
        """
        Params : model ... Model instance
                test_user_ids ... List of user_id which test_feats, validation input, was taken from
                test_feats ... List of numerical values, which is an input to the model
                test_target ... List of 0 (ham) and 1 (spam) labelled by curators
                save_path ... String of file path to save the model metrics json file
        Output : json file ... This stores model scores and user_ids used to validate the model. The format is as follows.
                 {"Accuracy": float, "Precision": float, "Recall": float, "F1",float, "test_user_ids": list of user_id}
        Returns : predictions ... List of predictions made by the model. Consists of 0 (ham) and 1 (spam).
                  model_metrics ... Dictionary of the same format as the output json file.
        """
        predictions, _ = self.get_predictions(model, test_feats)
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
    
    def load_model(self, file_path:str):
        if not os.path.isfile(file_path):
            self.fit()
        with open(file_path, "rb") as file:
            return pickle.load(file)

    def save_model(self, model, file_path:str):
        with open(file_path, "wb") as file:
            pickle.dump(model, file)

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

    def __convert_text_to_lowercase(self, text: str):
        return text.lower()

    def __replace_urls_with_webtag(self, text: str):
        return re.sub(r"http\S+|www\S+", " webtag ", text)

    def __replace_numbers_with_zero(self, text: str):
        return re.sub(r"\d+", " 0 ", text)

    def __remove_markdown(self, text: str):
        return re.sub(r"<.*?>", " ", text)

    def __remove_excess_spaces(self, text: str):
        return re.sub(r"\s+", " ", text)


class TextSpamClassifier(SpamClassifier):
    def __init__(self):
        super().__init__()
        self.MODEL_FILE_PATH = SPAM_DIR_PATH / "text_classifier.pkl"
        self.MODEL_METRICS_FILE_PATH = SPAM_DIR_PATH / "text_classifier_metrics.json"

    def fit(self):
        model = Pipeline(
            [
                ("cleaner", FunctionTransformer(self.preprocess)),
                ("countvectorizer", CountVectorizer(lowercase=True)),
                ("classifier", MultinomialNB()),
            ]
        )

        all_df = self.processor.get_all_users_df()

        if all_df.empty:
            return None

        data_x, data_y = self.concat_pd(all_df)
        if data_x.empty:
            return None
        
        print(len(data_y.value_counts()))
        if len(data_y.value_counts()) != 2: 
            print("Cannot create a binary classifier!!")
            return None

        (
            train_x,
            test_x,
            train_y,
            test_y,
        ) = train_test_split(data_x, data_y, test_size=0.1, random_state=434)

        model.fit(train_x["text"], train_y)
        self.save_model(model, self.MODEL_FILE_PATH)
        test_predictions, model_metrics = self.validate_model(
            model,
            test_x["user_id"].tolist(),
            test_x["text"].tolist(),
            test_y.tolist(),
            self.MODEL_METRICS_FILE_PATH,
        )
        return model_metrics

    def predict(self):
        df = self.processor.get_unlabelled_by_curator_df()
        if df.empty:  # no-op if no data found
            return []

        model = self.load_model(self.MODEL_FILE_PATH)
        data_x, data_y = self.concat_pd(df)
        if data_x.empty:
            return []
        
        predictions, confidences = self.get_predictions(model, data_x["text"])

        # save the results to DB
        result = {"user_id" : data_x["user_id"],
                  "text_classifier_confidence": confidences,
                  "labelled_by_text_classifier": predictions
        }
        df = pd.DataFrame(result).replace(np.nan, None)

        self.processor.update_predictions(df, isTextClassifier=True)
        return df["user_id"].values.flatten()

    def concat_pd(self, df):
        bio = df[["user_id", "bio", "labelled_by_curator"]][df["bio"] != ""]
        research_interests = df[
            ["user_id", "research_interests", "labelled_by_curator"]
        ][df["research_interests"] != ""]

        bio = bio.rename(columns={"bio": "text"})
        research_interests = bio.rename(columns={"research_interests": "text"})

        train_x = pd.concat(
            [bio[["user_id", "text"]], research_interests[["user_id", "text"]]]
        )

        train_y = pd.concat(
            [bio["labelled_by_curator"], research_interests["labelled_by_curator"]]
        )
        return train_x, train_y



class UserMetadataSpamClassifier(SpamClassifier):
    def __init__(self):
        SpamClassifier.__init__(self)
        self.MODEL_FILE_PATH = SPAM_DIR_PATH / "user_meta_classifier.pkl"
        self.MODEL_METRICS_FILE_PATH = SPAM_DIR_PATH / "user_meta_classifier_metrics.json"

    def fit(self):
        model = Pipeline(
            [
                ("cleaner", FunctionTransformer(self.preprocess)),
                ("countvectorizer", CountVectorizer(lowercase=True)),
                ("classifier", xgb.XGBClassifier()),
            ]
        )
        # obtain df from pipleline
        df = self.processor.get_all_users_df()
        if df.empty:
            return None # if no untrained data found
        
        if len(df['labelled_by_curator'].value_counts()) != 2:
            print("Cannot create a binary classifier!!")
            return None
        
        feats, targets = self.__input_df_transformation(df)
        (
            train_feats,
            test_feats,
            train_targets,
            test_targets,
        ) = train_test_split(feats, targets, test_size=0.1, random_state=434)

        model.fit(train_feats["text"], train_targets)
        self.save_model(model, self.MODEL_FILE_PATH)
        test_predictions, model_metrics = self.validate_model(
            model,
            test_feats["user_id"].tolist(),
            test_feats["text"].tolist(),
            test_targets["labelled_by_curator"].tolist(),
            self.MODEL_METRICS_FILE_PATH,
        )
        return model_metrics
    

    def predict(self):
        df = self.processor.get_unlabelled_by_curator_df()
        if df.empty:  # no-op if no data found
            return []

        model = self.load_model(self.MODEL_FILE_PATH)

        feats, targets = self.__input_df_transformation(df)

        predictions, confidences = self.get_predictions(model, feats["text"])

        # save the results to DB
        result = {"user_id" : feats["user_id"],
                  "user_classifier_confidence": confidences,
                  "labelled_by_user_classifier": predictions
        }
        df = pd.DataFrame(result).replace(np.nan, None)

        self.processor.update_predictions(df, isTextClassifier=False)
        return df["user_id"].values.flatten()
    
    def __input_df_transformation(self, df: pd.DataFrame):
        # extract relavant columns and reform data of some columns
        if "labelled_by_curator" not in df.columns:
            df["labelled_by_curator"] = 0  # only when mode='predict'

        df = df[[
                "user_id",
                "labelled_by_curator",
                "first_name",
                "last_name",
                "is_active",
                "email",
                "affiliations",
                "bio",
                "research_interests"
            ]]
        df[["first_name", "last_name", "is_active", "email", "affiliations", "bio", "research_interests"]] = df[["first_name", "last_name", "is_active", "email", "affiliations", "bio", "research_interests"]].fillna("")
        df[["user_id", "labelled_by_curator"]] = df[["user_id", "labelled_by_curator"]].fillna(0)

        df['text'] =  df.apply(lambda row:self.__create_text(row), axis=1)
        target = df[["labelled_by_curator"]]
        df = df[['text', 'user_id']]
        return df, target

    def __create_text(self, row):
        return self.__name(row) + self.__is_active(row['is_active'] )\
                                        + self.__email(row['email'])\
                                        + self.__affiliations(row['affiliations'])\
                                        + self.__bio(row['bio'])\
                                        + self.__research_interests(row['research_interests'])

    def __name(self, row):
        pre_string = "My name is "
        result = ""
        if row['first_name'] != 'NaN':
            result = pre_string + row['first_name']
            if row['last_name'] != "NaN":
                result = result + " " + row['last_name']
            result = result + ". "
        elif row['last_name'] != "NaN":
            result = pre_string + row['last_name'] + ". "
        return result

    def __is_active(self, val):
        if val == "t":
            return "I am an active user. "
        else:
            return "I am not an active user. "

    def __email(self, val):
        if val != 'NaN':
            return "My email address is " + val + ". "
        else:
            return ""

    def __affiliations(self, array):
        array = literal_eval(array)
        if len(array) != 0:
            pre_string = "I'm affiliated with the following organizations: "
            result = pre_string
            for affili_dict in array:
                name = affili_dict["name"] if ('name' in affili_dict.keys()) else "NaN"
                url = affili_dict["url"] if ('url' in affili_dict.keys()) else "NaN"
                ror_id = affili_dict["ror_id"] if ('ror_id' in affili_dict.keys()) else "NaN"
                affili = name + "(" + "url : " + url +", ror id : " + ror_id +")"
                result = result +", "+ affili
            return result + ". "
        else:
            return ""

    def __bio(self, val):
        if val != 'NaN':
            return val + " "
        else:
            return ""

    def __research_interests(self, val):
        if val != 'NaN':
            return "My research interests: " + val + ". "
        else:
            return ""