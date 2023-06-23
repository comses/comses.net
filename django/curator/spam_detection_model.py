import re
import pickle
from ast import literal_eval
import json
import os.path
from typing import List

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
from curator.models import SpamRecommendation

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




class SpamClassifier:
    TOKENIZER_FILE_PATH = 'tokenizer.pkl'
    MODEL_FILE_PATH = 'spam_xgb_classifier.pkl'

    def train(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df()

        # preprocess
        X_train, X_test, y_train, y_test = self.preprocess(df, 'train')

        # train
        prediction, metrics, model = self.train_xgboost_classifer(X_train, X_test, y_train, y_test)

        # save model
        pickle.dump(model, open(self.MODEL_FILE_PATH, 'wb'))

        # return model_metrics # if needed
        return None
    
    def partial_train(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df() #TODO Aiko: filter data that wasn't used for previous training

        # preprocess
        X, y, _ = self.preprocess(df, 'partial_train')

        # load model
        model = pickle.load(open(self.MODEL_FILE_PATH, 'rb'))

        # partial train
        model = self.partial_train_xgboost_classifer(X, y, model)

        # save model
        pickle.dump(model, open(self.MODEL_FILE_PATH, 'wb'))

        return None

    def predict(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df() #TODO Aiko: filter only the ones with no prediction

        # preprocess
        X, _, uid_series = self.preprocess(df, 'predict')

        # load model
        model = pickle.load(open(self.MODEL_FILE_PATH, 'rb'))

        # predict 
        confidence_socres = self.predict_xgboost_classifer(X, model)
        
        # create return df
        confidence_socres_series = pd.Series(confidence_socres)
        frame = {'user_id': uid_series.ravel() , 'labelled_by_bio_classifier': confidence_socres_series.ravel()} #TODO Aiko: reutrn confidence level also
        df = pd.DataFrame(frame)
        return df
    
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
        #TODO add logic for validating the model for user
        retrained_model = xgb.XGBClassifier()
        retrained_model.fit(X, y, xgb_model = old_model.get_booster())
        return retrained_model

    def predict_xgboost_classifer(self, X, model):
        probas = model.predict_proba(X)
        confidence_socres = list(map(lambda x: x[1], probas))
        return confidence_socres
    

    def preprocess(self, df, mode='predict'):
        # extract relavant columns
        df['labelled_by_curator'] = df['labelled_by_curator'].fillna(0)
        df = df.fillna('')
        df = df.filter(['user_id','labelled_by_curator','first_name','last_name', 'is_active', 'email', 'affiliations', 'bio'], axis=1)
        df['affiliations'] =  df.apply(lambda row:self.__reform__affiliations(row['affiliations']), axis=1)
        df['is_active'] =  df.apply(lambda row:self.__reform__is_active(row['is_active']), axis=1)

        # tokenize
        y = df['labelled_by_curator']
        X = df.drop(['labelled_by_curator'], axis = 1)
        if mode=='train':
            isTraining = True
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=434)
            tokenized_X_train = self.__preprocess_tokenization(X_train.drop(['user_id'],axis=1), isTraining)
            tokenized_X_test = self.__preprocess_tokenization(X_test.drop(['user_id'],axis=1))
            return tokenized_X_train, tokenized_X_test, y_train, y_test
        
        elif mode=='partial_train':
            isTraining = True
            uid_series = X.filter(['user_id'],axis=1).squeeze()
            tokenized_X = self.__preprocess_tokenization(X.drop(['user_id'],axis=1), isTraining)
            return tokenized_X, y, uid_series
    
        elif mode=='predict':
            uid_series = X.filter(['user_id'],axis=1).squeeze()
            tokenized_X = self.__preprocess_tokenization(X.drop(['user_id'],axis=1))
            return tokenized_X, y, uid_series
    

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
        else:
            return ""

    def __reform__is_active(self, val):
        if val == "t":
            return 1
        else:
            return 0
        
    def __preprocess__padding_sequences(self, column, tokenizer):
        word_index = tokenizer.word_index
        # total_words = len(word_index)  # get total_words of this coulmn's set
        column_sequences = tokenizer.texts_to_sequences(column) # tokenize
        # if max_len == None:
        #     sequences_lens = [len(n) for n in column_sequences] # get len() of each item
        #     max_len = sequences_lens[np.argmax(sequences_lens)]
        column_padded = pad_sequences(column_sequences, # padding
                                    maxlen = 800,
                                    padding =  'post',
                                    truncating =  'post')
        return list(column_padded), tokenizer


    def __preprocess__tokenize_test_column(self, column, tokenizer):
        return self.__preprocess__padding_sequences(column, tokenizer)

    def __preprocess__tokenize_train_column(self, column):
        tokenizer = Tokenizer(num_words = 2000, 
                        char_level = True,
                        oov_token =  '<OOV>')
        tokenizer.fit_on_texts(column)
        return self.__preprocess__padding_sequences(column, tokenizer)

    def __preprocess__tokenize_partial_train_column(self, column, tokenizer):
        tokenizer.fit_on_texts(column) # add new vocabraries
        return self.__preprocess__padding_sequences(column, tokenizer)


    def __preprocess__concatinate_row(self, row):
        input_data = np.concatenate((row['first_name'], row['last_name'], np.array([row['is_active']]), row['email'], row['affiliations'], row['bio']))
        return input_data
    

    def __preprocess_tokenization(self, X, isTraining=False):
        # create or load tokenizer
        tokenized_X_dict = {}
        tokenizer_dict = {}
        tokenize_info_dict = {}
        
        if isTraining: # initil-train or partial-train
            if os.path.exists(self.TOKENIZER_FILE_PATH): # partial-train
                tokenize_info_dict = pickle.load(open(self.TOKENIZER_FILE_PATH, 'rb'))
                tokenizer_dict = tokenize_info_dict['tokenizer']
                for col in X.columns:
                    if col == "is_active":
                        continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.__preprocess__tokenize_partial_train_column(X[col], tokenizer_dict[col])
                with open('first_name_tokenizer_config2.json','w') as fp: #TODO erase later
                    json.dump(tokenizer_dict['first_name'].get_config(),fp)
            else: # initil-train
                for col in X.columns:
                    if col == "is_active":
                        continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.__preprocess__tokenize_train_column(X[col])
                with open('first_name_tokenizer_config1.json','w') as fp: #TODO erase later
                    json.dump(tokenizer_dict['first_name'].get_config(),fp)

            tokenize_info_dict = {'tokenizer':tokenizer_dict}
            pickle.dump(tokenize_info_dict, open(self.TOKENIZER_FILE_PATH, 'wb')) # update file

        else: # predict
            tokenize_info_dict = pickle.load(open(self.TOKENIZER_FILE_PATH, 'rb'))
            # maxlen_dict = tokenize_info_dict['maxlen']
            tokenizer_dict = tokenize_info_dict['tokenizer']
            for col in X.columns:
                if col == "is_active":
                    continue
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
