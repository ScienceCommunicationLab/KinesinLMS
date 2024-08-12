import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.management.utils import duplicate_course

logger = logging.getLogger(__name__)

User = get_user_model()


class TestDuplicateCourse(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.course = CourseFactory()
        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

    def test_duplicate_course_utility_method(self):
        self.client.force_login(self.admin_user)
        dup_course = duplicate_course(self.course, new_slug="SLUG_COPY", new_run="RUN_COPY")
        self.assertEqual(f"SLUG_COPY", dup_course.slug)
        self.assertEqual(f"RUN_COPY", dup_course.run)
