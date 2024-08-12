from datetime import timedelta

from django.test import TestCase
from unittest.mock import patch

from django.utils.timezone import now
from rest_framework import status

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.tests.factories import UserFactory

import logging

logger = logging.getLogger(__name__)


class TestCourseAccessViews(TestCase):

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course
        self.no_enrollment_user = UserFactory(username="no-enrollment-user",
                                              email="no-enrollment-user@example.com")
        self.enrolled_user = UserFactory(username="enrolled-user",
                                         email="enrolled-user@example.com")
        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    # Test access...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_course_access_if_enrolled(self):
        course_base_url = self.course.course_url
        Enrollment.objects.get_or_create(student=self.enrolled_user,
                                                               course=self.course,
                                                               active=True)
        self.client.force_login(self.enrolled_user)
        response = self.client.get(course_base_url)
        expected_redirect_url = "/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_1/"
        self.assertRedirects(response, expected_redirect_url)

    # Test access denied...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_no_course_access_if_course_not_yet_released(self):
        tomorrow = now() + timedelta(days=1)
        course_2 = CourseFactory(slug="START_TOMORROW_COURSE", run="2020", start_date=tomorrow)
        course_2_base_url = course_2.course_url
        enrollment, created = Enrollment.objects.get_or_create(student=self.enrolled_user,
                                                               course=course_2,
                                                               active=True)
        self.client.force_login(self.enrolled_user)
        response = self.client.get(course_2_base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_course_access_if_not_logged_in(self):
        # User is not logged in...
        self.client.logout()
        course_base_url = self.course.course_url
        response = self.client.get(course_base_url)
        self.assertRedirects(response, '/accounts/login/?next=%2Fcourses%2FTEST%2FSP%2Fcontent%2F')

    def test_no_course_access_if_not_enrolled(self):
        course_base_url = self.course.course_url
        self.client.force_login(self.no_enrollment_user)
        response = self.client.get(course_base_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


