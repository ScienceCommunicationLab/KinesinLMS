import logging
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from kinesinlms.badges.tests.factories import BadgeProviderFactory
from kinesinlms.badges.models import BadgeAssertion
from kinesinlms.course.models import Enrollment, CoursePassed
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.models import UserSettings
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestBadgeAssertions(TestCase):
    """
    Test badge assertion API.
    """

    enrolled_user = None
    course = None
    patchers = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.patchers = []

        badge_provider = BadgeProviderFactory.create()
        cls.badge_provider = badge_provider

        # CourseFactory should build course completion Milestone and BadgeClass,
        # which we'll need set up first in order to test badges.
        course = CourseFactory(enable_badges=True)
        cls.course_base_url = course.course_url
        cls.course = course

        cls.course_passed_badge_class = course.badge_classes.first()

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
        cls.api_base_url = f"https://localhost:8000/api/"

    @classmethod
    def tearDownClass(cls):
        super(TestBadgeAssertions, cls).tearDownClass()
        for patcher in cls.patchers:
            patcher.stop()

    def test_create_badge_assertion(self):
        """
        Test that a student who passed a course can create a
        badge assertion (which happens via an API call when
        student clicks "Generate Badge")
        """

        # Make sure student enabled badges...
        settings: UserSettings = self.enrolled_user.get_settings()
        settings.enable_badges = True
        settings.save()

        # Make the course offer badges
        self.course.enable_badges = True
        self.course.save()

        # Have the student pass the course
        CoursePassed.objects.create(student=self.enrolled_user, course=self.course)

        badge_class_id = self.course_passed_badge_class.id

        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}badge_assertions/"
        data = {
            "badge_class_id": badge_class_id
        }

        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), BadgeAssertion.objects.count())

    def test_user_cannot_generate_badge_for_course_that_does_not_offer_badges(self):
        # Make sure student enabled badges...
        settings: UserSettings = self.enrolled_user.get_settings()
        settings.enable_badges = True
        settings.save()

        # Make sure the student *did not* pass course
        try:
            course_passed = CoursePassed.objects.get(student=self.enrolled_user, course=self.course)
            course_passed.delete()
        except CoursePassed.DoesNotExist:
            pass

        # Make the course *not* offer badges
        self.course.enable_badges = False
        self.course.save()

        # Have the student pass the course
        CoursePassed.objects.create(student=self.enrolled_user, course=self.course)

        badge_class_id = self.course_passed_badge_class.id

        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}badge_assertions/"
        data = {
            "badge_class_id": badge_class_id
        }

        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_generate_badge_for_course_they_did_not_pass(self):

        # Make sure student enabled badges...
        settings: UserSettings = self.enrolled_user.get_settings()
        settings.enable_badges = True
        settings.save()

        # Make sure the student *did not* pass course
        try:
            course_passed = CoursePassed.objects.get(student=self.enrolled_user, course=self.course)
            course_passed.delete()
        except CoursePassed.DoesNotExist:
            pass

        # Make the course offer badges
        self.course.enable_badges = True
        self.course.save()

        badge_class_id = self.course_passed_badge_class.id

        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}badge_assertions/"
        data = {
            "badge_class_id": badge_class_id
        }

        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_generate_badge_for_course_they_are_not_enrolled_in(self):

        # Make sure student enabled badges...
        settings: UserSettings = self.enrolled_user.get_settings()
        settings.enable_badges = True
        settings.save()

        # Make the course offer badges
        self.course.enable_badges = True
        self.course.save()

        # Remove student from enrollment
        Enrollment.objects.get(student=self.enrolled_user,
                               course=self.course).delete()

        badge_class_id = self.course_passed_badge_class.id

        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}badge_assertions/"
        data = {
            "badge_class_id": badge_class_id
        }

        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
