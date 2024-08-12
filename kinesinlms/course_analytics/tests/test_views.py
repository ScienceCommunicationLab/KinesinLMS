import logging
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from kinesinlms.course.models import CourseStaffRole, Enrollment
from kinesinlms.course.tests.factories import CourseFactory, CourseStaffFactory
from kinesinlms.users.tests.factories import EducatorFactory, UserFactory
from kinesinlms.users.utils import create_default_groups

logger = logging.getLogger(__name__)


class TestCourseAccessViews(TestCase):
    def setUp(self):
        create_default_groups()
        
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        self.superuser_user = UserFactory(
            username="superuser-user",
            is_superuser=True,
            email="superuser-user@example.com",
        )

        self.staff_user = UserFactory(
            username="staff-user",
            is_superuser=False,
            is_staff=True,
            email="staff-user@example.com",
        )

        self.course_educator = EducatorFactory(
            username="course-educator-user",
            is_superuser=False,
            is_staff=False,
            email="course-educator@example.com",
        )

        self.course_educator_not_in_this_course = EducatorFactory(
            username="other-course-educator-user",
            is_superuser=False,
            is_staff=False,
            email="other-course-educator@example.com",
        )

        CourseStaffFactory.create(
            user=self.course_educator,
            course=course,
            role=CourseStaffRole.EDUCATOR.name,
        )

        self.no_enrollment_user = UserFactory(
            username="no-enrollment-user", email="no-enrollment-user@example.com"
        )

        self.enrolled_user = UserFactory(
            username="enrolled-user", email="enrolled-user@example.com"
        )

        Enrollment.objects.get_or_create(
            student=self.enrolled_user, course=self.course, active=True
        )

        # mock the calls to external tracking API
        self.patcher = patch("kinesinlms.tracking.tracker.Tracker.track")
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_course_analytics_access(self):
        course_analytics_url = reverse(
            "course:course_admin:course_analytics:index",
            kwargs={"course_slug": self.course.slug, "course_run": self.course.run},
        )

        # These users SHOULD be able to see the Analytics page

        self.client.force_login(self.superuser_user)
        response = self.client.get(f"{course_analytics_url}")
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.client.force_login(self.staff_user)
        response = self.client.get(f"{course_analytics_url}")
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.client.force_login(self.course_educator)
        response = self.client.get(f"{course_analytics_url}")
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        # These users SHOULD NOT be able to see the Analytics page

        self.client.force_login(self.course_educator_not_in_this_course)
        response = self.client.get(f"{course_analytics_url}")
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self.client.force_login(self.enrolled_user)
        response = self.client.get(f"{course_analytics_url}")
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
