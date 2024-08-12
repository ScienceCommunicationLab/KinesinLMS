import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)


class TestDiscourseAPI(TestCase):
    """
    Test all API endpoints related to this module.
    """

    enrolled_user = None
    course_1 = None

    @classmethod
    def setUpTestData(cls) -> None:
        super(TestDiscourseAPI, cls).setUpTestData()
        User = get_user_model()
        cls.enrolled_user = User.objects.create(username="enrolled-user")
        cls.other_user = User.objects.create(username="other-user")
        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

        course_1 = CourseFactory()
        cls.course_1 = course_1
        Enrollment.objects.get_or_create(student=cls.enrolled_user,
                                         course=cls.course_1,
                                         active=True)

        course_2 = CourseFactory(
            slug="SOME_OTHER_COURSE",
            run="2020",
            display_name="Some Other Course")
        cls.course_2 = course_2
        Enrollment.objects.get_or_create(student=cls.other_user,
                                         course=cls.course_2,
                                         active=True)

        cls.api_client = APIClient()
        cls.api_base_url = "https://localhost:8000/api/"

    # TODO : Implement tests for discourse topic view API
    # def test_student_using_discourse_widget_can_view_topic_discussion_via_api(self):
    #    """
    #    Make sure students can't access protected endpoints.
    #    :return:
    #    """
    #    self.client.force_login(self.enrolled_user)
