import logging

from django.test import TestCase

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/tracking/'


class TestTrackingService(TestCase):

    def setUp(self):
        pass
