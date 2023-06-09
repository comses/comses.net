import pandas as pd
import numpy as np
import pickle
from ast import literal_eval
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb
from curator.spam_detect import UserPipeline
import time
import json
import os.path

tokenizer_path = 'tokenizer.pkl'
model_path = 'spam_xgb_classifier.pkl'

class SpamClassifier:

    def preprocess_affiliations(self, array):
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

    def preprocess_active_status(self, val):
        if val == "t":
            return 1
        else:
            return 0
        

    def preprocess_get_pad_sequences(self, column, tokenizer):
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


    def preprocess_tokenize_test_column(self, column, tokenizer):
        return self.preprocess_get_pad_sequences(column, tokenizer)
    

    def preprocess_tokenize_train_column(self, column):
        tokenizer = Tokenizer(num_words = 2000, 
                        char_level = True,
                        oov_token =  '<OOV>')
        tokenizer.fit_on_texts(column)
        return self.preprocess_get_pad_sequences(column, tokenizer)
    

    def preprocess_tokenize_partial_train_column(self, column, tokenizer):
        tokenizer.fit_on_texts(column) # add new vocabraries
        return self.preprocess_get_pad_sequences(column, tokenizer)


    def preprocess_concatinate_tokenized_data(self, row):
        input_data = np.concatenate((row['first_name'], row['last_name'], np.array([row['is_active']]), row['email'], row['affiliations'], row['bio']))
        return input_data
    

    def preprocess_tokenization(self, X, isTraining=False):
        # create or load tokenizer
        tokenized_X_dict = {}
        # maxlen_dict = {}
        tokenizer_dict = {}
        tokenize_info_dict = {}
        
        if isTraining: # initil-train or partial-train
            if os.path.exists(tokenizer_path): # partial-train
                print(' partial-train')
                tokenize_info_dict = pickle.load(open(tokenizer_path, 'rb'))
                tokenizer_dict = tokenize_info_dict['tokenizer']
                for col in X.columns:
                    if col == "is_active":
                        continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.preprocess_tokenize_partial_train_column(X[col], tokenizer_dict[col])
                with open('first_name_tokenizer_config2.json','w') as fp: #TODO erase later
                    json.dump(tokenizer_dict['first_name'].get_config(),fp)
            else: # initil-train
                for col in X.columns:
                    if col == "is_active":
                        continue
                    tokenized_X_dict[col], tokenizer_dict[col] = self.preprocess_tokenize_train_column(X[col])
                with open('first_name_tokenizer_config1.json','w') as fp: #TODO erase later
                    json.dump(tokenizer_dict['first_name'].get_config(),fp)

            tokenize_info_dict = {'tokenizer':tokenizer_dict}
            pickle.dump(tokenize_info_dict, open(tokenizer_path, 'wb')) # update file

        else: # predict
            tokenize_info_dict = pickle.load(open(tokenizer_path, 'rb'))
            # maxlen_dict = tokenize_info_dict['maxlen']
            tokenizer_dict = tokenize_info_dict['tokenizer']
            for col in X.columns:
                if col == "is_active":
                    continue
                tokenized_X_dict[col], _ = self.preprocess_tokenize_test_column(X[col], tokenizer_dict[col])

        # apply tokenizer        
        tokenized_X = pd.DataFrame(columns=X.columns, index=X.index)
        for col in  X.columns:
            if col == "is_active":
                tokenized_X[col] = X[col]
                continue
            tokenized_X[col] = tokenized_X[col].astype(object)
            temp_df = pd.DataFrame({col : tokenized_X_dict[col]}, columns = [col], index=X.index )
            tokenized_X[col] = temp_df

        tokenized_X['input_data'] = tokenized_X.apply(lambda row:self.preprocess_concatinate_tokenized_data(row), axis=1)
        return np.array(tokenized_X['input_data'].tolist())


    def preprocess(self, df, mode='predict'):
        # extract relavant columns
        df['is_spam_labelled_by_curator'] = df['is_spam_labelled_by_curator'].fillna(0)
        df = df.fillna('')
        df = df.filter(['user_id','is_spam_labelled_by_curator','first_name','last_name', 'is_active', 'email', 'affiliations', 'bio'], axis=1)
        df['affiliations'] =  df.apply(lambda row:self.preprocess_affiliations(row['affiliations']), axis=1)
        df['is_active'] =  df.apply(lambda row:self.preprocess_active_status(row['is_active']), axis=1)

        # tokenize
        y = df['is_spam_labelled_by_curator']
        X = df.drop(['is_spam_labelled_by_curator'], axis = 1)
        if mode=='train':
            isTraining = True
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=434)
            tokenized_X_train = self.preprocess_tokenization(X_train.drop(['user_id'],axis=1), isTraining)
            tokenized_X_test = self.preprocess_tokenization(X_test.drop(['user_id'],axis=1))
            return tokenized_X_train, tokenized_X_test, y_train, y_test
        
        elif mode=='partial_train':
            isTraining = True
            uid_series = X.filter(['user_id'],axis=1).squeeze()
            tokenized_X = self.preprocess_tokenization(X.drop(['user_id'],axis=1), isTraining)
            return tokenized_X, y, uid_series
    
        elif mode=='predict':
            uid_series = X.filter(['user_id'],axis=1).squeeze()
            tokenized_X = self.preprocess_tokenization(X.drop(['user_id'],axis=1))
            return tokenized_X, y, uid_series
    

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
        #TODO add logic for validation
        retrained_model = xgb.XGBClassifier()
        retrained_model.fit(X, y, xgb_model = old_model.get_booster())
        return retrained_model

    def predict_xgboost_classifer(self, X, model):
        probas = model.predict_proba(X)
        confidence_socres = list(map(lambda x: x[1], probas))
        return confidence_socres

    def train(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df()

        df = df.iloc[:3000] #TODO erase later

        # preprocess
        X_train, X_test, y_train, y_test = self.preprocess(df, 'train')

        # train
        prediction, metrics, model = self.train_xgboost_classifer(X_train, X_test, y_train, y_test)
        pd.DataFrame(prediction).to_csv('train_prediction.csv')
        print(metrics)

        # save model
        pickle.dump(model, open(model_path, 'wb'))

        # return model_metrics # if needed
        return None
    
    def partial_train(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df() #TODO: let user choose

        df = df.iloc[3000:] #TODO erase late––

        # preprocess
        X, y, _ = self.preprocess(df, 'partial_train')

        # load model
        model = pickle.load(open(model_path, 'rb'))

        # partial train
        model = self.partial_train_xgboost_classifer(X, y, model)

        # save model
        pickle.dump(model, open(model_path, 'wb'))

        return None

    def predict(self):
        # obtain df from pipleline
        pipeline = UserPipeline()
        df = pipeline.all_users_df()

        # preprocess
        X, _, uid_series = self.preprocess(df, 'predict')

        # load model
        model = pickle.load(open(model_path, 'rb'))

        # predict 
        confidence_socres = self.predict_xgboost_classifer(X, model)
        
        # create return df
        confidence_socres_series = pd.Series(confidence_socres)
        frame = {'user_id': uid_series.ravel() , 'is_spam_labelled_by_classifier': confidence_socres_series.ravel()} #TODO Aiko: reutrn confidence level also
        df = pd.DataFrame(frame)
        return df