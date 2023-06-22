import time
import json
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

from curator.spam_detect import UserPipeline

from abc import ABC, abstractmethod


# TODO implement
class SpamDetection():
    def execute(self): # API for ML functions
        ''' 
            0, if there is some users that have None in eihter labelled_by_curator, labelled_by_user_classifier, 
                and labelled_by_bio_classifier, predict() should be called.

                1. if no model pickle files found, execute fit()
                    - if all labelled_by_curator is None, load to DB by calling Pipeline.load_labels()
                    - additionally, if no labels file, throw exception

                2. make sure model exitsts, call predict(). 
                   The function will save its results to the DB.
                    - BioSpamClassifier.predict()
                    - UserSpamClassifer.predict()

            3. filtering the DB, return the list of all user_id (and user name) with a certain confidence level (TODO: discussabout returns)
                    return UserPipeline.get_spam_users() # TODO: implement this function
                        ... this functions will first filter out the users with labelled_by_curator==True,
                            but the ones with None, 
                            only get users with labelled_by_user_classifier or labelled_by_bio_classifier == True with a specific confidence level

        '''
        return
    
    def refine_models(self):
        # TODO: use the newly updated labelled_by_user_classifier and call partial_train()?
        return


class SpamClassifier(ABC): 
    # This class serves as a template for spam classifer varients
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
        

class TextSpamClassifier(object):
    # This is temporary until we find a better solution.
    # We are saving and loading models straight to the VM,
    # ideally, we instead store it in some object storage instead.
    INITIAL_FILE_PATH = "curator/label.json"
    MODEL_FILE_PATH = "curator/instance.pkl"

    def load_model(): 
        if os.path.isfile(TextSpamClassifier.MODEL_FILE_PATH): TextSpamClassifier.fit()
        with open(TextSpamClassifier.MODEL_FILE_PATH, "rb") as file:
            return pickle.load(file)

    def save_model(model): 
        with open(TextSpamClassifier.MODEL_FILE_PATH, "wb") as file:
            pickle.dump(model, file)

    def fit(): 
        # TODO:
        model = Pipeline([
            ('cleaner', FunctionTransformer(TextSpamClassifier.preprocess)),
            ('countvectorizer', CountVectorizer(lowercase=True)),
            ('classifier', MultinomialNB())
        ])

        user_pipeline = UserPipeline()
        untrained_df = user_pipeline.get_untrained_df()
        
        if len(untrained_df) != 0: 
            bio = untrained_df[['bio', 'labelled_by_curator']][untrained_df['bio'] != ""]
            research_interests = untrained_df[['research_interests', 'labelled_by_curator']][untrained_df['research_interests'] != ""]

            train_x = pd.concat([bio['bio'], research_interests['research_interests']]).to_list()

            train_y = pd.concat([bio['labelled_by_curator'], research_interests['labelled_by_curator']])

            model.fit(train_x, train_y)

        TextSpamClassifier.save_model(model)

    def predict():
        user_pipeline = UserPipeline()
        all_users_df = user_pipeline.get_all_users_df()
        model = TextSpamClassifier.load_model()

        if len(all_users_df) != 0:
            model.predict(all_users_df['bio'].to_list())


    def preprocess(text_list : List[str]): 
        text_list = [TextSpamClassifier.__text_cleanup_pipeline(text) for text in text_list]
        return text_list

    def __text_cleanup_pipeline(text : str): 
        text = str(text)
        text = TextSpamClassifier.__convert_text_to_lowercase(text)
        text = TextSpamClassifier.__replace_urls_with_webtag(text)
        text = TextSpamClassifier.__replace_numbers_with_zero(text)
        text = TextSpamClassifier.__remove_markdown(text)
        text = TextSpamClassifier.__remove_excess_spaces(text)
        return text
    
    def __convert_text_to_lowercase(text : str): return text.lower()
    def __replace_urls_with_webtag(text : str): return re.sub(r'http\S+|www\S+', ' webtag ', text) 
    def __replace_numbers_with_zero(text : str): return re.sub(r'\d+', ' 0 ', text)
    def __remove_markdown(text : str): return re.sub(r'<.*?>', ' ', text)
    def __remove_excess_spaces(text : str): return re.sub(r'\s+', ' ', text)



class SpamClassifier(SpamClassifier):
    TOKENIZER_FILE_PATH = 'tokenizer.pkl'
    MODEL_FILE_PATH = 'spam_xgb_classifier.pkl'

    def fit(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.get_untrained_df()
        if df.empty == True: return # if no untrained data found

        X_train, X_test, y_train, y_test = self.preprocess(df, 'train') # preprocess

        prediction, metrics, model = self.train_xgboost_classifer(X_train, X_test, y_train, y_test) # train

        pickle.dump(model, open(self.MODEL_FILE_PATH, 'wb')) # save model

        pipeline.update_used_for_train(df) # save last trained date
        # return model_metrics # if needed

    
    def partial_fit(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.get_untrained_df()
        if df.empty == True: return # if no untrained data found

        X, y = self.preprocess(df, 'partial_train') # preprocess

        model = pickle.load(open(self.MODEL_FILE_PATH, 'rb')) # load model

        model = self.partial_train_xgboost_classifer(X, y, model) # partial train

        pickle.dump(model, open(self.MODEL_FILE_PATH, 'wb')) # save model

        pipeline.update_used_for_train(df) # save last trained date


    def predict(self):
        pipeline = UserPipeline()
        df = pipeline.get_unlabelled_by_curator_df()
        if df.empty == True: return # if no data found
                    
        X, _ = self.preprocess(df, 'predict') # preprocess

        model = pickle.load(open(self.MODEL_FILE_PATH, 'rb')) # load model

        predictions, confidences = self.predict_xgboost_classifer(X, model) # predict 
        df['labelled_by_user_classifier'] = predictions
        df['user_classifier_confidence'] = confidences
        df = df.filter(['user_id','user_classifier_confidence','labelled_by_user_classifier'], axis=1).replace(np.nan, None)
        pipeline.save_predictions(df, isTextClassifier=False) # save the results to DB

        # return result_df TODO we don't have to return this, do we?


    def train_xgboost_classifer(self, X_train, X_test, y_train, y_test):
        # fit to model
        model = xgb.XGBClassifier()
        model.fit(X_train, y_train)
        y_pred_xgb = model.predict(X_test)

        # get metrics
        accuracy = accuracy_score(y_test, y_pred_xgb)
        precision = precision_score(y_test, y_pred_xgb)
        recall = recall_score(y_test, y_pred_xgb)
        f1 = f1_score(y_test, y_pred_xgb)
        model_metrics = (accuracy, precision, recall, f1)
        return y_pred_xgb, model_metrics, model

    def partial_train_xgboost_classifer(self, X, y, old_model):
        # TODO add logic for validation
        retrained_model = xgb.XGBClassifier()
        retrained_model.fit(X, y, xgb_model=old_model.get_booster())
        return retrained_model

    def predict_xgboost_classifer(self, X, model):
        confidences = model.predict(X)
        predictions = [round(value) for value in confidences]
        # confidence_socres = list(map(lambda x: x[1], probas))
        return predictions, confidences
    
    def preprocess(self, df, mode='predict'):
        # extract relavant columns
        if 'labelled_by_curator' not in df.columns: df['labelled_by_curator'] = 0 # only when mode='predict' 
        df = df.filter(['user_id','labelled_by_curator','first_name','last_name', 'is_active', 'email', 'affiliations', 'bio'], axis=1)
        df[['first_name','last_name', 'is_active', 'email', 'affiliations', 'bio']] = df[['first_name','last_name', 'is_active', 'email', 'affiliations', 'bio']].fillna('') 
        df[['user_id', 'labelled_by_curator']] = df[['user_id', 'labelled_by_curator']].fillna(0)
        df['affiliations'] =  df.apply(lambda row:self.__reform__affiliations(row['affiliations']), axis=1)
        df['is_active'] =  df.apply(lambda row:self.__reform__is_active(row['is_active']), axis=1)

        # tokenize
        y = df['labelled_by_curator']
        X = df.drop(['labelled_by_curator'], axis = 1)
        isTraining = False
        if mode=='train':
            isTraining = True
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=434)
            tokenized_X_train = self.__preprocess__tokenization(X_train.drop(['user_id'],axis=1), isTraining)
            tokenized_X_test = self.__preprocess__tokenization(X_test.drop(['user_id'],axis=1))
            return tokenized_X_train, tokenized_X_test, y_train, y_test
        elif mode=='partial_train':
            isTraining = True

        # default mode is prediction 
        tokenized_X = self.__preprocess__tokenization(X.drop(['user_id'],axis=1), isTraining)
        return tokenized_X, y
    
    
    def __reform__affiliations(self, array):
        array = literal_eval(array)
        if len(array) != 0:
            result = ""
            for affili_dict in array:
                name = affili_dict["name"] if ('name' in affili_dict.keys()) else "NaN"
                url = affili_dict["url"] if ('url' in affili_dict.keys()) else "NaN"
                ror_id = affili_dict["ror_id"] if ('ror_id' in affili_dict.keys()) else "NaN"
                affili = name + "(" + "url : " + url +", ror id : " + ror_id +")"
                result = result +", "+ affili
            return result + ". "
        else: return ""

    def __reform__is_active(self, val):
        if val == "t": return 1
        else: return 0
        
    def __preprocess__padding_sequences(self, column, tokenizer):
        column_sequences = tokenizer.texts_to_sequences(column) # tokenize
        column_padded = pad_sequences(column_sequences, maxlen=800, padding='post', truncating='post')
        return list(column_padded), tokenizer

    def __preprocess__tokenize_test_column(self, column, tokenizer):
        return self.__preprocess__padding_sequences(column, tokenizer)

    def __preprocess__tokenize_train_column(self, column):
        tokenizer = Tokenizer(num_words=2000, char_level=True, oov_token='<OOV>')
        tokenizer.fit_on_texts(column)
        return self.__preprocess__padding_sequences(column, tokenizer)

    def __preprocess__tokenize_partial_train_column(self, column, tokenizer):
        tokenizer.fit_on_texts(column) # add new vocabularies
        return self.__preprocess__padding_sequences(column, tokenizer)

    def __preprocess__concatinate_row(self, row):
        input_data = np.concatenate((row['first_name'], row['last_name'], np.array([row['is_active']]), row['email'], row['affiliations'], row['bio']))
        return input_data
    
    def __preprocess__tokenization(self, X, isTraining=False):
        # create or load tokenizer
        tokenized_X_dict = {}
        tokenizer_dict = {}
        tokenize_info_dict = {}
        
        if isTraining: # initil-train or partial-train
            if os.path.exists(self.TOKENIZER_FILE_PATH): # partial-train
                tokenize_info_dict = pickle.load(open(self.TOKENIZER_FILE_PATH, 'rb'))
                tokenizer_dict = tokenize_info_dict['tokenizer']
                for col in X.columns:
                    if col == "is_active": continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.__preprocess__tokenize_partial_train_column(X[col], tokenizer_dict[col])
            else: # initil-train
                for col in X.columns:
                    if col == "is_active": continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.__preprocess__tokenize_train_column(X[col])

            tokenize_info_dict = {'tokenizer':tokenizer_dict}
            pickle.dump(tokenize_info_dict, open(self.TOKENIZER_FILE_PATH, 'wb')) # update file

        else: # prediction
            tokenize_info_dict = pickle.load(open(self.TOKENIZER_FILE_PATH, 'rb'))
            # maxlen_dict = tokenize_info_dict['maxlen']
            tokenizer_dict = tokenize_info_dict['tokenizer']
            for col in X.columns:
                if col == "is_active": continue
                tokenized_X_dict[col], _ = self.__preprocess__tokenize_test_column(X[col], tokenizer_dict[col])

        # apply tokenizer        
        tokenized_X = pd.DataFrame(columns=X.columns, index=X.index)
        for col in  X.columns:
            if col == "is_active":
                tokenized_X[col] = X[col]
                continue
            tokenized_X[col] = tokenized_X[col].astype(object)
            temp_df = pd.DataFrame({col : tokenized_X_dict[col]}, columns = [col], index=X.index )
            tokenized_X[col] = temp_df

        tokenized_X['input_data'] = tokenized_X.apply(lambda row:self.__preprocess__concatinate_row(row), axis=1)
        return np.array(tokenized_X['input_data'].tolist())
