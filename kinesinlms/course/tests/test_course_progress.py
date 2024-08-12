import logging
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from kinesinlms.course.models import Enrollment
from kinesinlms.course.nav import get_course_nav
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestCourseProgress(TestCase):

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course
        self.no_enrollment_user = UserFactory(username="no-enrollment-user",
                                              email="no-enrollment-user@example.com")
        self.enrolled_user = UserFactory(username="enrolled-user",
                                         email="enrolled-user@example.com")
        Enrollment.objects.get_or_create(student=self.enrolled_user,
                                         course=self.course,
                                         active=True)
        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    # Test access...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_can_view_overview_page(self):
        course_base_url = reverse('course:progress_overview_page', kwargs={'course_slug': self.course.slug,
                                                                           'course_run': self.course.run})
        self.client.force_login(self.enrolled_user)
        response = self.client.get(course_base_url)
        self.assertTrue(status.HTTP_200_OK, response.status_code)
        html_content = response.content.decode('utf-8')
        self.assertIn("id=\"course-progress-nav\"", html_content)

    def test_can_view_detail_page(self):
        course_base_url = reverse('course:progress_detail_page', kwargs={'course_slug': self.course.slug,
                                                                         'course_run': self.course.run})
        self.client.force_login(self.enrolled_user)
        response = self.client.get(course_base_url)
        self.assertTrue(status.HTTP_200_OK, response.status_code)
        html_content = response.content.decode('utf-8')
        self.assertIn("id=\"course-progress-nav\"", html_content)

    def test_can_view_module_detail_page(self):
        # Try viewing one of the modules...
        course_nav = get_course_nav(self.course)
        selected_module = course_nav['children'][1]
        selected_module_id = selected_module['id']
        expected_total_assessments_for_module = 2

        course_base_url = reverse('course:module_progress_detail_page', kwargs={'course_slug': self.course.slug,
                                                                                'course_run': self.course.run,
                                                                                'module_id': selected_module_id
                                                                                })
        self.client.force_login(self.enrolled_user)
        response = self.client.get(course_base_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        html_content = response.content.decode('utf-8')
        self.assertIn("Module Progress", html_content)
        self.assertEqual(response.context['progress_status'].milestones[0].item_type, 'Assessment')
        self.assertEqual(response.context['progress_status'].milestones[0].item_count, expected_total_assessments_for_module)

    def test_cannot_view_overview_page_if_not_enrolled_in(self):
        course_base_url = reverse('course:progress_overview_page', kwargs={'course_slug': self.course.slug,
                                                                           'course_run': self.course.run})
        self.client.force_login(self.no_enrollment_user)
        response = self.client.get(course_base_url)
        self.assertTrue(status.HTTP_403_FORBIDDEN, response.status_code)
