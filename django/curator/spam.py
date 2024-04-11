import logging
from enum import Enum
from django.conf import settings

from .spam_processor import UserSpamStatusProcessor
from . import spam_classifiers
from .spam_classifiers import (
    SpamClassifier,
    Encoder,
    CategoricalFieldEncoder,
    XGBoostClassifier,
    CountVectEncoder
)
from sklearn.model_selection import train_test_split
logger = logging.getLogger(__name__)
logging.captureWarnings(True)
processor = UserSpamStatusProcessor()


class PresetContextID(Enum):
    """
    Preset fields
    1 : email, affiliations, bio
    2 : email, affiliations, bio, is_active
    3 : email, affiliations, bio, personal_url, professional_url
    """
    XGBoost_CountVect_1 = 'XGBoostClassifier CountVectEncoder PresetFields1'
    XGBoost_CountVect_2 = 'XGBoostClassifier CountVectEncoder PresetFields2'
    XGBoost_CountVect_3 = 'XGBoostClassifier CountVectEncoder PresetFields3'
    XGBoost_Bert_1 =      'XGBoostClassifier BertEncoder PresetFields1'
    NNet_CountVect_1 = 'NNetClassifier CountVectEncoder PresetFields1'
    NNet_Bert_1 =      'NNetClassifier BertEncoder PresetFields1'
    NaiveBayes_CountVect_1 = 'NaiveBayesClassifier CountVectEncoder PresetFields1'
    NaiveBayes_Bert_1 =      'NaiveBayesClassifier BertEncoder PresetFields1'

    @classmethod
    def fields(cls, context_id_value:str):
        # if 'PresetFields1' in context_id
        field_list = ['email', 'affiliations', 'bio']
        if 'PresetFields2' in context_id_value:
            field_list.append('is_active')
        elif 'PresetFields3' in context_id_value:
            field_list.extend(['personal_url', 'professional_url'])
        return field_list
    
    @classmethod
    def choices(cls):
        print(tuple((i.value, i.name) for i in cls))
        return tuple((i.value, i.name) for i in cls)
    
class XGBoost_CountVect_1():
    def create():
        pass

class SpamDetectionContext():
    def __init__(self, contex_id:PresetContextID):
        self.contex_id = contex_id
        self.classifer:SpamClassifier = None
        self.encoder:Encoder = None
        self.categorical_encoder = CategoricalFieldEncoder()
        self.selected_fields = []
        self.selected_categorical_fields = []
    
    def set_classifer(self, classifer:SpamClassifier):
        self.classifer = classifer

    def set_encoder(self, encoder:Encoder):
        self.encoder = encoder

    def set_fields(self, fields:list):
        '''
        <Params>
        fields: [field_names]
                field_name: ex) 'first_name, 'last_name, 'is_active, etc
        '''
        self.selected_fields = fields
        self.selected_categorical_fields = [field for field in self.selected_fields if field in processor.field_type['categorical']]

    def get_model_metrics(self)->dict:
        metrics = self.classifer.load_metrics()
        metrics.pop('test_user_ids')
        return metrics

    def train(self, user_ids:list[int]=None):
        if not user_ids:
            df = processor.get_all_users_with_label(self.selected_fields)
        else:
            df = processor.get_selected_users_with_label(user_ids, self.selected_fields)

        self.categorical_encoder.set_categorical_fields(self.selected_categorical_fields)
        df = self.categorical_encoder.encode(df)

        labels = df["label"]
        feats = df.drop('label', axis=1)
        feats = self.encoder.encode(feats)

        (
            train_feats,
            test_feats,
            train_labels,
            test_labels,
        ) = train_test_split(feats, labels, test_size=0.1, random_state=434)

        model = self.classifer.train(train_feats, train_labels)
        model_metrics = self.classifer.evaluate(model, test_feats, test_labels)
        self.classifer.save(model)
        self.classifer.save_metrics(model_metrics)

    def predict(self, user_ids:list[int]=None):
        if not user_ids:
            df = processor.get_all_users(self.selected_fields)
        else:    
            df = processor.get_selected_users(user_ids, self.selected_fields)  #TODO check

        self.categorical_encoder.set_categorical_fields(self.selected_categorical_fields)
        df = self.categorical_encoder.encode(df)

        feats = self.encoder.encode(df)
        
        model = self.classifer.load()
        result_df = self.classifer.predict(model, feats)
        processor.save_predictions(result_df, self.contex_id)

    
class SpamDetectionContextFactory():
    """
    This class generates a context with a preset combination of [encoder, classifier, fields]
    """
    @classmethod
    def create(cls, context_id=PresetContextID.XGBoost_CountVect_1)->SpamDetectionContext:
        spam_detection_contex = SpamDetectionContext(context_id)
        context_id_value = context_id.value.split()

        classifier_class_ = getattr(spam_classifiers, context_id_value[0])
        selected_classifier = classifier_class_(context_id.name)
        spam_detection_contex.set_classifer(selected_classifier)

        encoder_class_ = getattr(spam_classifiers, context_id_value[1])
        selected_encoder = encoder_class_(context_id.name)
        spam_detection_contex.set_encoder(selected_encoder)

        selected_fields = PresetContextID.fields(context_id.value)
        spam_detection_contex.set_fields(selected_fields)

        return spam_detection_contex