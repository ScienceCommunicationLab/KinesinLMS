import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)


class TestAssessmentsAPIExtra(TestCase):
    """
    Test strange extra conditions or edge
    cases for API acces.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        User = get_user_model()
        enrolled_user = User.objects.create(username="enrolled-user")
        cls.enrolled_user = enrolled_user
        admin_user = User.objects.create(username="daniel",
                                         is_staff=True,
                                         is_superuser=True)
        cls.admin_user = admin_user

        course = CourseFactory(self_paced=True)
        cls.course = course

        Enrollment.objects.get_or_create(student=enrolled_user,
                                         course=course,
                                         active=True)

        cls.api_client = APIClient()
        cls.api_base_url = f"https://localhost:8000/api/"

    # The following unit test won't be needed anymore. It's an error condition
    # to do a POST on an existing answer, so it shouldn't happen, and we shouldn't
    # expect to accomodate it.

    """
    def test_answer_already_exists(self):
        # Sometimes I see errors in the log where a student tried to save a new
        # answer (a post instead of a put) but an answer already existed in the server.
        # This is strange b/c if an answer already existed, the React client should have issued
        # a put. At any rate, the server code in the create method of the serializer should
        # accept the answer and overwrite the existing answer as if an "update" was issued.
  
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        assessment_block = course_unit.contents.filter(type=BlockType.ASSESSMENT.name).first()
        assessment = assessment_block.assessment

        # add an existing answer
        answer = SubmittedAnswerFactory(course=self.course,
                                        assessment=assessment,
                                        student=self.enrolled_user)

        # Make sure the answer is there
        url = f"{self.api_base_url}answers/{answer.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now issue a POST (not a PUT) and see if the create method updates the existing answer
        url = f"{self.api_base_url}answers/"
        data = {
            "assessment": assessment.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "answer": f"An updated answer for assessment {assessment.id} I already answered."
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        answer = SubmittedAnswer.objects.get(assessment=assessment, course=self.course, student=self.enrolled_user)
        self.assertIn(f"A new answer for assessment {assessment.id}", answer)
"""
