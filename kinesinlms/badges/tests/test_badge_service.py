import logging
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIClient

from kinesinlms.badges.service import BadgrBadgeService
from kinesinlms.badges.models import BadgeAssertion, BadgeClass
from kinesinlms.badges.tests.factories import BadgeProviderFactory, BadgeClassFactory
from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestBadgrIntegration(TestCase):
    """
    This is a quick set of integration tests to make sure we can create a badge assertion on Badgr.
    These tests assume:
     - the user and password for a Badgr account have been set in the env.
     - an issuer and badge class have been created in Badgr for this test
    """

    enrolled_user = None
    course = None
    patchers = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.patchers = []

        badge_provider = BadgeProviderFactory.create()
        cls.badge_provider = badge_provider

        # This CourseFactory should create a related Milestone, BadgeClass
        course = CourseFactory(enable_badges=True)
        cls.course_base_url = course.course_url
        cls.course = course

        cls.enrolled_user = UserFactory(username="enrolled-user",
                                        email="enrolled-user@example.com")

        # mock the calls to external tracking API
        patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        patcher.start()
        cls.patchers.append(patcher)

        Enrollment.objects.get_or_create(student=cls.enrolled_user,
                                         course=cls.course,
                                         active=True)
        cls.api_client = APIClient()
        cls.api_base_url = "https://localhost:8000/api/"

        course_passed_badge_class = BadgeClassFactory.create(provider=badge_provider, course=course)
        cls.course_passed_badge_class = course_passed_badge_class

    @classmethod
    def tearDownClass(cls):
        super(TestBadgrIntegration, cls).tearDownClass()
        for patcher in cls.patchers:
            patcher.stop()

    @skipUnless(settings.TEST_BADGE_PROVIDER_ISSUER_ID, "Badge Service Provider not configured")
    @skipUnless(settings.TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID, "Badge Class not configured")
    @skipUnless(settings.BADGE_PROVIDER_USERNAME, "Badge provider username not configured")
    @skipUnless(settings.BADGE_PROVIDER_PASSWORD, "Badge provider password not configured")
    def test_badgr_service_integration(self):
        """
        This is a quick integration test to make sure we can create a badge assertion on Badgr.
        """

        # So we're really calling Badgr here and expecting a good response.
        badge_provider = self.course_passed_badge_class.provider
        badge_provider.api_url = "https://api.badgr.io/"

        badge_assertion = BadgeAssertion.objects.create(badge_class=self.course_passed_badge_class,
                                                        recipient=self.enrolled_user,
                                                        issued_on=now())

        service = BadgrBadgeService(badge_provider=badge_provider)
        success = service.create_remote_badge_assertion(badge_assertion=badge_assertion)
        self.assertTrue(success)
