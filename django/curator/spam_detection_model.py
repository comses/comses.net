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
        

    def preprocess_get_pad_sequences(self, column, tokenizer, max_len):
        word_index = tokenizer.word_index
        # total_words = len(word_index)  # get total_words of this coulmn's set
        column_sequences = tokenizer.texts_to_sequences(column) # tokenize
        if max_len == None:
            sequences_lens = [len(n) for n in column_sequences] # get len() of each item
            max_len = sequences_lens[np.argmax(sequences_lens)]
        column_padded = pad_sequences(column_sequences, # padding
                                    maxlen = max_len,
                                    padding =  'post',
                                    truncating =  'post')
        return list(column_padded), tokenizer, max_len


    def preprocess_tokenize_test_column(self, column, tokenizer, max_len):
        return self.preprocess_get_pad_sequences(column, tokenizer, max_len)


    def preprocess_tokenize_train_column(self, column):
        tokenizer = Tokenizer(num_words = 2000, 
                        char_level = True,
                        oov_token =  '<OOV>')
        tokenizer.fit_on_texts(column)
        max_len = None
        return self.preprocess_get_pad_sequences(column, tokenizer, max_len)


    def preprocess_concatinate_tokenized_data(self, row):
        input_data = np.concatenate((row['first_name'], row['last_name'], np.array([row['is_active']]), row['email'], row['affiliations'], row['bio']))
        return input_data
    

    def preprocess_tokenization(self, X, isTraining=False):
        # print (tokenized_X.shape)

        # create or load tokenizer
        tokenized_X_dict = {}
        maxlen_dict = {}
        tokenizer_dict = {}
        tokenize_info_dict = {}
        if isTraining:
            for col in X.columns:
                if col == "is_active":
                    continue
                tokenized_X_dict[col], tokenizer_dict[col], maxlen_dict[col] = self.preprocess_tokenize_train_column(X[col])
            tokenize_info_dict = {'maxlen':maxlen_dict , 'tokenizer':tokenizer_dict}
            pickle.dump(tokenize_info_dict, open('tokenizer.pkl', 'wb'))
        else:
            tokenize_info_dict = pickle.load(open('tokenizer.pkl', 'rb'))
            maxlen_dict = tokenize_info_dict['maxlen']
            tokenizer_dict = tokenize_info_dict['tokenizer']
            for col in X.columns:
                if col == "is_active":
                    continue
                tokenized_X_dict[col], _, _ = self.preprocess_tokenize_test_column(X[col], tokenizer_dict[col], maxlen_dict[col])

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


    def preprocess(self, df, isTraining=False):
        # extract relavant columns
        df['is_spam'] = df['is_spam'].fillna(0)
        df = df.fillna('')
        df = df.filter(['user_id','is_spam','first_name','last_name', 'is_active', 'email', 'affiliations', 'bio'], axis=1)
        df['affiliations'] =  df.apply(lambda row:self.preprocess_affiliations(row['affiliations']), axis=1)
        df['is_active'] =  df.apply(lambda row:self.preprocess_active_status(row['is_active']), axis=1)

        # tokenize
        y = df['is_spam']
        X = df.drop(['is_spam'], axis = 1)
        if isTraining:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=434)
            # uid_train = X_train.filter(['user_id'],axis=1) #TODO
            # uid_test = X_test.filter(['user_id'],axis=1) #TODO
            tokenized_X_train = self.preprocess_tokenization(X_train.drop(['user_id'],axis=1), isTraining)
            tokenized_X_test = self.preprocess_tokenization(X_test.drop(['user_id'],axis=1))
            return tokenized_X_train, tokenized_X_test, y_train, y_test
        
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

    def inference_xgboost_classifer(self, X, model):
        probas = model.predict_proba(X)
        confidence_socres = list(map(lambda x: x[1], probas))
        return confidence_socres

    def train(self):
        # obtain df from pipleline
        start = time.time()
        pipeline = UserPipeline()
        df = pipeline.all_users_df()
        # end = time.time()
        # print(end - start)
        # print(df)

        # preprocess
        isTraining = True
        X_train, X_test, y_train, y_test = self.preprocess(df, isTraining)

        # train
        _, _, model = self.train_xgboost_classifer(X_train, X_test, y_train, y_test)

        # save model
        pickle.dump(model, open('spam_xgb_classifier.pkl', 'wb'))
        # end = time.time()
        # print(end - start)

        # return model_metrics # if needed
        return None
    
    def partial_train(self): # TODO: add option of how old the data is
        # obtain df from pipleline
        start = time.time()
        pipeline = UserPipeline()
        df = pipeline.all_users_df() #TODO: let user choose
        # end = time.time()
        # print(end - start)
        # print(df)

        # preprocess
        isTraining = False
        X, y, _ = self.preprocess(df, isTraining)

        # load model
        model = pickle.load(open('spam_xgb_classifier.pkl', 'rb'))

        # partial train
        model = self.partial_train_xgboost_classifer(X, y, model)

        # save model
        pickle.dump(model, open('spam_xgb_classifier.pkl', 'wb'))
        # end = time.time()
        # print(end - start)

        return None

    def inference(self):
        # obtain df from pipleline
        start = time.time()
        pipeline = UserPipeline()
        df = pipeline.all_users_df()
        # end = time.time()
        # print(end - start)
        # print(df)

        # preprocess
        isTraining = False
        X, _, uid_series = self.preprocess(df, isTraining)

        # load model
        model = pickle.load(open('spam_xgb_classifier.pkl', 'rb'))

        # inference 
        confidence_socres = self.inference_xgboost_classifer(X, model)
        
        # create return df
        confidence_socres_series = pd.Series(confidence_socres)
        frame = {'user_id': uid_series.ravel() , 'spam_likely': confidence_socres_series.ravel()}
        df = pd.DataFrame(frame)
        # end = time.time()
        # print(end - start)
        return df