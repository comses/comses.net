import logging

from django.core.management.base import BaseCommand
from curator.spam import SpamDetectionContextFactory, SpamDetectionContext, PresetContextID
from curator.spam_processor import UserSpamStatusProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Perform spam detection'
    def __init__(self) -> None:
        self.context:SpamDetectionContext = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--context_id',
            '-id',
            type=str,
            default='XGBoost_CountVect_1',
            help='Classifier options: UserMetadata or Text',
        )    
        parser.add_argument(
            '--predict',
            '-p',
            action='store_true',
            default=False,
            help='Print user_ids of spam users and the metrics of the models used to obtain the predictions.',
        )
        parser.add_argument(
            '--fit',
            '-f',
            action='store_true',
            default=False,
            help='Fit all models based on user data labelled by curator.',
        )
        parser.add_argument(
            '--get_model_metrics',
            '-m',
            action='store_true',
            default=False,
            help='Print the accuracy, precision, recall and f1 scores of the models used to obtain the predictions.',
        )
        parser.add_argument(
            '--load_labels',
            '-l',
            action='store_true',
            default=False,
            help='Store bootstrap spam labels to the DB.',
        )

    def handle_predict(self):
        self.context.predict()
    
    def handle_fit(self):
        self.context.train()

    def handle_get_model_metrics(self):
        socre_dict = self.context.get_model_metrics()
        logger.info(socre_dict.pop('test_user_ids'))
         #TODO tentative
        logger.info('The list of user_ids can be found in the metrics json file, which was used to calculate the scores.')

    def handle_load_labels(self):
        self.processor = UserSpamStatusProcessor()
        self.processor.load_labels_from_csv()

    def handle(self, *args, **options):
        context_id_string = options['context_id']
        if options['predict']:
            action = 'predict'
        elif options['fit']:
            action = 'fit'
        elif options['get_model_metrics']:
            action = 'get_model_metrics'
        elif options['load_labels']:
            action = 'load_labels'

        context_id = PresetContextID[context_id_string]
        self.context = SpamDetectionContextFactory.create(context_id)
        getattr(self, f'handle_{action}')()
