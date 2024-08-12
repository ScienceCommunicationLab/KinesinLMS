import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from rest_framework import status
from rest_framework.test import APIClient
from selenium.webdriver.firefox.webdriver import WebDriver
from unittest import skipUnless

from kinesinlms.badges.models import BadgeAssertion, BadgeClass
from kinesinlms.course.models import Enrollment, CourseUnit, Milestone
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.users.tests.factories import UserFactory

User = get_user_model()
logger = logging.getLogger(__name__)

TEST_USER_NAME = "test-student"
TEST_USER_PW = "test-student-pw-123"


class TestBadges(StaticLiveServerTestCase):
    """

    This integration test is designed to make sure KinesinLMS is successfully connecting
    to the Badgr API and getting Badgr to award a badge assertion when a student 
    completes a course.

    IMPORTANT: In order to run this test, you must have the following environment
    variables set:
     -  TEST_BADGE_PROVIDER_ISSUER_ID:              The ID of the issuer for the badge class
     -  TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID:  The ID of the badge class

    Also, for the test to complete, the following conditions must be met:
        - Student settings must have badges_enabled.
        - Course must have badges_enabled
        - Course must have a milestone set that is required for passing course.
    ... this test shoud set those conditions before running the test.

    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.selenium = WebDriver()
            cls.selenium.implicitly_wait(10)
        except Exception:
            cls.selenium = None
            # Couldn't load selenium...we're probably running on Heroku
            # TODO Tried using pytest skip statements but couldn't get them to work
            # TODO so just using a simpler mechanism of checking whether class variable is set.
            logger.exception("Can't find Selenium...skipping MySeleniumTests")

        course = CourseFactory()
        cls.course_base_url = course.course_url
        cls.course = course
        user = UserFactory.create()
        user.save()

        # Setting up the Course via the CourseFactory should have created a badge.

        email_address, created = EmailAddress.objects.get_or_create(user=user,
                                                                    email=user.email)
        email_address.primary = True
        email_address.verified = True
        email_address.save()

        # Make sure student is enrolled
        enrollment = Enrollment.objects.create(course=course,
                                               student=user,
                                               active=True)
        cls.enrollment = enrollment
        cls.enrolled_user = user

        cls.api_client = APIClient()
        cls.api_base_url = "https://localhost:8000/api/"

    @classmethod
    def tearDownClass(cls):
        if cls.selenium:
            cls.selenium.quit()
        super(TestBadges, cls).tearDownClass()

    @skipUnless(settings.TEST_BADGE_PROVIDER_ISSUER_ID, "Badge Service Provider not configured")
    @skipUnless(settings.TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID, "Badge Class not configured")
    @skipUnless(settings.BADGE_PROVIDER_USERNAME, "Badge provider username not configured")
    @skipUnless(settings.BADGE_PROVIDER_PASSWORD, "Badge provider password not configured")
    def test_earn_badge(self):
        """
        Answer one assessment, which should cause the student to pass the test and
        earn a badge.
        """

        # SANITY CHECKS before running the test:
        # make sure badges are enabled
        self.assertTrue(self.course.enable_badges)
        # make sure there's a badgeclass for this course
        BadgeClass.objects.get(course=self.course)
        # make sure there's a milestone set
        Milestone.objects.get(course=self.course, required_to_pass=True)

        # Now answer one assessment, which should trigger course passed and therefore
        # badge earned.
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        assessment_block = course_unit.contents.filter(type=BlockType.ASSESSMENT.name).first()
        assessment = assessment_block.assessment
        url = f"{self.api_base_url}answers/"
        data = {
            "assessment": assessment.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "answer": "My answer to the long form question."
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Now make sure badge assertion has valid information with urls that
        # point to something real.
        badge_assertion = BadgeAssertion.objects.get(recipient=self.enrolled_user)
        self.assertIsNotNone(badge_assertion.open_badge_id)
        self.assertIn("https://api.badgr.io/", badge_assertion.open_badge_id)
