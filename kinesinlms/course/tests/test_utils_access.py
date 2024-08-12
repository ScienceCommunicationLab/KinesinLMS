import logging
from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now

from kinesinlms.course.utils_access import can_access_course_unit_in_course, can_access_course, get_course_node_lineage
from kinesinlms.course.constants import NodeType
from kinesinlms.course.models import CourseNode
from kinesinlms.course.tests.factories import CourseFactory, EnrollmentFactory
from kinesinlms.course.views import get_course_nav
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestCourseUtils(TestCase):

    @classmethod
    def setUpTestData(cls):
        course = CourseFactory()
        cls.course_base_url = course.course_url
        cls.course = course
        cls.no_enrollment_user = UserFactory(username="no-enrollment-user",
                                             email="no-enrollment-user@example.com")
        enrolled_user = UserFactory(username="enrolled-user",
                                    email="enrolled-user@example.com")
        cls.enrolled_user = enrolled_user
        cls.enrollment = EnrollmentFactory(student=enrolled_user,
                                           course=course)

    # Test helper methods...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_get_course_node_lineage(self):
        """
        Test the get_course_node_lineage() method
        """

        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        first_course_unit = first_unit_node.unit
        course_nav = get_course_nav(course=self.course)
        course_nodes = course_nav['children']

        # method should return three nodes representing
        # unit, section and module (in that order)
        lineage = get_course_node_lineage(course_unit=first_course_unit,
                                          course_nodes=course_nodes)
        self.assertTrue(len(lineage) == 3)

    # Test access...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_can_access_course(self):
        """
        Test can_access_course method allows access.
        """
        # Course started yesterday, should be available.
        self.course.start_date = now() - timedelta(days=1)
        self.course.save()
        result = can_access_course(user=self.enrolled_user, course=self.course)
        self.assertTrue(result)

    def test_cannot_access_course(self):
        """
        Test can_access_course method disallows access.
        """
        # Course started tomorrow, should NOT be available.
        self.course.start_date = now() + timedelta(days=1)
        self.course.save()
        result = can_access_course(user=self.enrolled_user, course=self.course)
        self.assertFalse(result)

    def test_beta_user_can_access_course(self):
        """
        Test can_access_course when user is beta-test and course
        has beta test days early set.
        """
        # Course starts in 8 days, but beta tester should have access 10 days early
        # so course should be available
        self.enrollment.beta_tester = True
        self.enrollment.save()
        self.course.days_early_for_beta = 10
        self.course.start_date = now() + timedelta(days=8)
        self.course.save()
        result = can_access_course(user=self.enrolled_user, course=self.course)
        self.assertTrue(result)

    def test_beta_user_cannot_access_course(self):
        """
        Test can_access_course when user is beta-test and course
        has beta test days set, but it's still too early to access.
        """
        # Course starts in 12 days, and beta tester should have access 10 days early
        # so course should NOT be available
        self.course.start_date = now() + timedelta(days=12)
        self.course.save()
        result = can_access_course(user=self.enrolled_user, course=self.course)
        self.assertFalse(result)

    def test_can_access_course_unit(self):
        """
        Test the can_access_course_unit_in_course() method return True
        when UNIT node has release date of yesterday.
        """

        # Assume course is released but that we've got units with different release dates.
        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit
        first_unit_node.release_datetime = now() - timedelta(1)
        first_unit_node.save()

        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertTrue(result)

    def test_cannot_access_course_unit(self):
        """
        Test the can_access_course_unit_in_course() method returns
        false when UNIT node has release date for tomorrow.
        """

        # Assume course is released but that we've got units with different release dates.
        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit
        first_unit_node.release_datetime = now() + timedelta(1)
        first_unit_node.save()
        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertFalse(result)

    def test_can_access_course_unit_when_section_not_released(self):
        """
        Test the can_access_course_unit_in_course() method return True
        when SECTION node has release date of yesterday.
        """

        # Assume course is released but that we've got units with different release dates.

        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit

        first_section_node: CourseNode = CourseNode.objects.filter(type=NodeType.SECTION.name).first()
        first_section_node.release_datetime = now() - timedelta(1)
        first_section_node.save()

        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertTrue(result)

    def test_cannot_access_course_unit_when_section_not_released(self):
        """
        Test the can_access_course_unit_in_course() method return False
        when SECTION node has release date of tomorrow.
        """

        # Assume course is released but that we've got units with different release dates.

        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit

        first_section_node: CourseNode = CourseNode.objects.filter(type=NodeType.SECTION.name).first()
        first_section_node.release_datetime = now() + timedelta(1)
        first_section_node.save()

        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertFalse(result)

    def test_can_access_course_unit_when_module_not_released(self):
        """
        Test the can_access_course_unit_in_course() method return True
        when MODULE node has release date of yesterday.
        """

        # Assume course is released but that we've got units with different release dates.

        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit

        first_module_node: CourseNode = CourseNode.objects.filter(type=NodeType.MODULE.name).first()
        first_module_node.release_datetime = now() - timedelta(1)
        first_module_node.save()

        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertTrue(result)

    def test_cannot_access_course_unit_when_module_not_released(self):
        """
        Test the can_access_course_unit_in_course() method return False
        when MODULE node has release date of tomorrow.
        """

        # Assume course is released but that we've got units with different release dates.

        first_unit_node: CourseNode = CourseNode.objects.filter(type=NodeType.UNIT.name).first()
        course_unit = first_unit_node.unit

        first_module_node: CourseNode = CourseNode.objects.filter(type=NodeType.MODULE.name).first()
        first_module_node.release_datetime = now() + timedelta(1)
        first_module_node.save()

        course_nav = get_course_nav(self.course)
        result = can_access_course_unit_in_course(course_unit=course_unit,
                                                  user=self.enrolled_user,
                                                  course_nav=course_nav)
        self.assertFalse(result)
