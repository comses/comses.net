from django.test import TestCase

from curator.spam_detection_models import SpamDetection


class SpamDetectionTestCase(TestCase):
    def setUp(self):
        self.detection = SpamDetection()


"""
TODO:

1. After initializing SpamDetection(), check the 
"""
