from abc import ABC, abstractmethod
import json
import pickle
import logging
import numpy as np
from  pandas import DataFrame

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
    def train(self, train_feats, train_labels)->object: # return model object
        pass

    @abstractmethod
    def predict(self, model, feats, confidence_threshold=0.5)->DataFrame:
        pass

    @abstractmethod
    def evaluate(self, model, test_feats, test_labels)->dict:
        pass

    @abstractmethod
    def load(self)->object: # return model object
        pass

    @abstractmethod
    def save(self, model):
        pass

    @abstractmethod
    def load_metrics(self):
        pass

    @abstractmethod
    def save_metrics(self, model_metrics:dict):
        pass

class Encoder(ABC):
    """
    This class serves as a template for encoder variants
    """
    @abstractmethod
    def encode(self, feats:DataFrame)->DataFrame:
        """
        TODO: 
        """
        pass


class XGBoostClassifier(SpamClassifier):
    def __init__(self, context_id:str):
        self.context_id = context_id
        self.model_folder = SPAM_DIR_PATH/context_id
        self.model_folder.mkdir(parents=True, exist_ok=True)
        self.classifier_path = self.model_folder/'model.pkl'
        self.metrics_path = self.model_folder/'metrics.json'

    def train(self, train_feats, train_labels):
        logger.info("Training XGBoost classifier....")
        model = XGBClassifier()
        model.fit(np.array(train_feats['input_data'].tolist()), train_labels.tolist())
        return model

    def predict(self, model:XGBClassifier, feats, confidence_threshold=0.5):
        logger.info("Predicting using XGBoost classifier....")
        probas = model.predict_proba(
            np.array(feats['input_data'].tolist())
        )  # predict_proba() outputs a list of list in the format with [(probability of 0(ham)), (probability of 1(spam))]
        probas = [value[1] for value in probas]
        preds = [int(p >= confidence_threshold) for p in probas]
        # preds = [round(value) for value in confidences]
        result = {
            "user_id": feats['user_id'].tolist(),
            "confidences": probas,
            "predictions": preds,
        }
        result_df = DataFrame(result).replace(np.nan, None)
        return result_df

    def evaluate(self, model:XGBClassifier, test_feats, test_labels):
        logger.info("Evaluating XGBoost classifier....")
        result = self.predict(model, test_feats)
        accuracy = round(accuracy_score(test_labels, result['predictions']), 3)
        precision = round(precision_score(test_labels, result['predictions']), 3)
        recall = round(recall_score(test_labels, result['predictions']), 3)
        f1 = round(f1_score(test_labels, result['predictions']), 3)
        model_metrics = {
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "test_user_ids": test_feats["user_id"].tolist(),
        }
        return model_metrics

    def load(self)->XGBClassifier:
        """
        Load model instance that was trained and saved previously.

        Params : file_path ... Path to the saved model instance
        Returns : Loaded model instance
        """
        try:
            file = open(self.classifier_path, "rb")
            with file:
                model = pickle.load(file)
                return model
        except OSError:
            logger.info("Could not open/read file: {0}".format(self.classifier_path))


    def save(self, model:XGBClassifier):
        """
        Save model instance that was trained.

        Params : model ... model instance XGBClassifier
        """
        self.model_folder.mkdir(parents=True, exist_ok=True)
        with open(self.classifier_path, "wb") as file:
            pickle.dump(model, file)

    #TODO ask: have save_metrics and load_metrics? or only save()
    def load_metrics(self)->dict:
        try:
            file = open(self.metrics_path, "r")
            with file:
                model_metrics = json.load(file)
                return model_metrics
        
        except OSError:
            logger.info("Could not open/read file:{0}".format(self.metrics_path))

    def save_metrics(self, model_metrics:dict):
        """
        Save model scores.

        Params : model_metrics ... dict with the model scores such as Accuracy, Precision, etc..
        """
        with open(self.metrics_path, "w") as file:
            json.dump(model_metrics, file, indent=4)



class CategoricalFieldEncoder(Encoder):
    def __init__(self):
        self.categorical_fields = []

    def set_categorical_fields(self, categorical_fields):
        self.categorical_fields = categorical_fields

    def encode(self, feats: DataFrame)->DataFrame:
        for col in self.categorical_fields:
            le = LabelEncoder()
            feats[col] = le.fit_transform(feats[col].tolist())
        return feats
        

class CountVectEncoder(Encoder):
    def __init__(self, context_id:str):
        self.context_id = context_id
        self.model_folder = SPAM_DIR_PATH/context_id
        self.model_folder.mkdir(parents=True, exist_ok=True)
        self.encoder_path = self.model_folder/'encoder.pkl'
        self.char_analysis_fields = ['first_name', 'last_name', 'email_username', 'email_domain']

    def set_char_analysis_fields(self, char_analysis_fields):
        self.char_analysis_fields = char_analysis_fields

    def encode(self, feats:DataFrame)->DataFrame:
        def get_encoded_sequences(data:list, vectorizer:CountVectorizer):
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
                encoded_df[col] =  feats[col]
                continue

            vectorized_seqs = get_encoded_sequences(feats[col], encoders_dict[col])
            encoded_df[col] = DataFrame({col : vectorized_seqs}, columns=[col], index=feats.index)
        return self.__concatenate(encoded_df)
    
    def __fit(self, feats:DataFrame):
        def fit_vectorizer(data, analyzer='word', ngram_range=(1,1)):
            return CountVectorizer(analyzer=analyzer, ngram_range=ngram_range).fit(data)
        
        encoders_dict = {}
        # print(feats.dtypes)
        # print(feats.head())
        for col in feats.columns:
            data_list = feats[col].tolist()
            if feats[col].dtype == np.int64 or feats[col].dtype == int:
                continue
            if col in self.char_analysis_fields:
                vectorizer = fit_vectorizer(data_list, analyzer='char', ngram_range=(1,1))
            else:
                vectorizer = fit_vectorizer(data_list)
            encoders_dict[col] = vectorizer
        return encoders_dict

    def __load(self):
        try:
            file = open(self.encoder_path, "rb")
            with file:
                encoders_dict = pickle.load(file)
                return encoders_dict
        except OSError:
            logger.info("Could not open/read file:{0}".format(self.encoder_path))

    def __save(self, encoders_dict:dict):
        self.model_folder.mkdir(parents=True, exist_ok=True)
        with open(self.encoder_path, "wb") as file:
            pickle.dump(encoders_dict, file)

    def __concatenate(self, encoded_df:DataFrame):
        columnlist = [col for col in encoded_df.columns if col!='user_id' and col!='input_data']
        def concatinate_tokenized_data(row):
            input_data = []
            for col in columnlist:
                if isinstance(row[col],np.ndarray):
                    input_data = input_data + row[col].tolist()
                else:
                    input_data.append(row[col])
            return input_data

        encoded_df['input_data'] = encoded_df.apply(concatinate_tokenized_data, axis=1)
        return encoded_df[['user_id', 'input_data']] # dataframe with columns ['user_id', 'input_data']