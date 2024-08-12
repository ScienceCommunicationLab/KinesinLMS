import logging
from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from kinesinlms.badges.models import BadgeAssertion
from kinesinlms.badges.tests.factories import BadgeProviderFactory
from kinesinlms.course.models import Enrollment, CourseUnit
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestBadgeAssertions(TestCase):
    """
    Test badge assertions.
    """

    patchers = None
    course = None
    enrolled_user = None

    @classmethod
    def setUpTestData(cls) -> None:

        super().setUpTestData()
        patchers = []

        badge_provider = BadgeProviderFactory.create()
        cls.badge_provider = badge_provider

        cls.patchers = patchers
        # mock the calls to external tracking API
        patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        patcher.start()
        patchers.append(patcher)

        # CourseFactory should build course completion Milestone and BadgeClass,
        # which we'll need set up first in order to test badges.
        course = CourseFactory(enable_badges=True)
        cls.course = course
        cls.course_base_url = course.course_url

        cls.course_passed_badge_class = course.badge_classes.first()

        enrolled_user = UserFactory(username="enrolled-user",
                                    email="enrolled-user@example.com")
        cls.enrolled_user = enrolled_user

        Enrollment.objects.get_or_create(student=enrolled_user,
                                         course=course,
                                         active=True)
        cls.api_client = APIClient()
        cls.api_base_url = f"https://localhost:8000/api/"

    @classmethod
    def tearDownClass(cls):
        super(TestBadgeAssertions, cls).tearDownClass()
        for patcher in cls.patchers:
            patcher.stop()

    def test_student_earns_course_passed_badge(self):
        """
        Test that a student earns a badge assertion after meeting
        the requirements of a Milestone with a required_to_pass=True setting.
        """

        # Before starting, make sure there's just one milestone, and it's required_to_pass
        milestone = self.course.milestones.get(course=self.course)
        self.assertTrue(milestone.required_to_pass)
        # and make sure badge assertion doesn't exist yet
        course_passed_badge_class = milestone.badge_class
        with self.assertRaises(ObjectDoesNotExist):
            BadgeAssertion.objects.get(recipient=self.enrolled_user,
                                       badge_class=course_passed_badge_class)

        # Have student answer three assessments
        self.api_client.force_login(self.enrolled_user)
        course_units = CourseUnit.objects.all()[:3]
        for course_unit in course_units:
            assessment_block = course_unit.contents.filter(type=BlockType.ASSESSMENT.name).first()
            assessment = assessment_block.assessment
            logger.debug(f"Answering assessment : {assessment}")
            url = f"{self.api_base_url}answers/"
            data = {
                "assessment": assessment.id,
                "course": self.course.id,
                "course_unit": course_unit.id,
                "json_content": {
                    "answer": f"My answer to the long form question in course_unit {course_unit}."
                }
            }
            response = self.api_client.post(url, data=data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure badge assertion was created
        badge_assertion = BadgeAssertion.objects.get(badge_class=self.course_passed_badge_class,
                                                     recipient=self.enrolled_user)
        todays_date = timezone.now().date
        self.assertTrue(badge_assertion.issued_on.date, todays_date)

        catalog_url = reverse('catalog:index')
        response = self.client.get(catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
