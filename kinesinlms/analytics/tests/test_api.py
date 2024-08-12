import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)


class TestAPI(TestCase):
    """
    Test all API endpoints related to this module.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super(TestAPI, cls).setUpTestData()
        User = get_user_model()
        enrolled_user = User.objects.create(username="enrolled-user")
        cls.enrolled_user = enrolled_user
        admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)
        cls.admin_user = admin_user

        course = CourseFactory()
        cls.course = course

        Enrollment.objects.get_or_create(student=enrolled_user,
                                         course=course,
                                         active=True)

        cls.api_base_url = "https://localhost:8000/api/analytics/"
        cls.api_client = APIClient()

    def test_get_engagement(self):
        self.api_client.force_login(self.admin_user)
        url = f"{self.api_base_url}engagement/{self.course.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_data = response.data[0]
        self.assertEqual(course_data['course_token'], self.course.token)
        progresses = course_data['progresses']
        self.assertEqual(progresses[0]['student'], self.enrolled_user.id)

    def test_all_api_access_disallowed_to_anon_users(self):
        self.api_client.logout()
        self._call_methods_on_endpoint(expected_status=status.HTTP_401_UNAUTHORIZED)

    def test_all_api_access_disallowed_to_student_users(self):
        self.api_client.force_login(self.enrolled_user)
        self._call_methods_on_endpoint(expected_status=status.HTTP_403_FORBIDDEN)

    def _call_methods_on_endpoint(self, expected_status):
        engagement_for_course_url = f"{self.api_base_url}engagement/{self.course.id}/"
        response = self.api_client.get(engagement_for_course_url)
        self.assertEqual(response.status_code, expected_status)

        response = self.api_client.post(engagement_for_course_url, data={})
        self.assertEqual(response.status_code, expected_status)

        response = self.api_client.put(engagement_for_course_url, data={})
        self.assertEqual(response.status_code, expected_status)

        response = self.api_client.patch(engagement_for_course_url, data={})
        self.assertEqual(response.status_code, expected_status)

        response = self.api_client.delete(engagement_for_course_url, data={})
        self.assertEqual(response.status_code, expected_status)
