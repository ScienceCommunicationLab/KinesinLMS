import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)


class TestDashboardViews(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        course = CourseFactory()
        User = get_user_model()
        enrolled_user = User.objects.create(username="enrolled-user")
        enrollment, created = Enrollment.objects.get_or_create(student=enrolled_user,
                                                               course=course,
                                                               active=True)
        cls.enrollment = enrollment
        cls.course = course
        cls.enrolled_user = enrolled_user

    def setUp(self):
        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_dashboard_index_context_has_enrolled_courses(self):
        self.client.force_login(self.enrolled_user)
        index_url = reverse('dashboard:index')
        response = self.client.get(index_url)
        self.assertEqual(response.status_code, 200)
        context_enrollments = [course['enrollment'] for course in response.context['courses_info']]
        self.assertQuerySetEqual(Enrollment.objects.filter(student=self.enrolled_user), context_enrollments)
