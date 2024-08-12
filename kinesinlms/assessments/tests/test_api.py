import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient

from kinesinlms.assessments.models import Assessment
from kinesinlms.assessments.tests.factories import SubmittedAnswerFactory
from kinesinlms.course.models import Enrollment, CourseUnit
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.constants import BlockType

logger = logging.getLogger(__name__)


class TestAssessmentsAPI(TestCase):
    """
    Test all API endpoints related to this module.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super(TestAssessmentsAPI, cls).setUpTestData()
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

    # TEST ASSESSMENT ENDPOINTS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_admin_can_list_assessments(self):
        self.api_client.force_login(self.admin_user)
        url = f"{self.api_base_url}assessments/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Assessment.objects.count())

    def test_admin_can_view_assessment_detail(self):
        existing_assessment = Assessment.objects.first()
        self.api_client.force_login(self.admin_user)
        url = f"{self.api_base_url}assessments/{existing_assessment.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_list_assessments(self):
        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}assessments/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_view_assessment_detail(self):
        existing_assessment = Assessment.objects.first()
        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}assessments/{existing_assessment.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_rest_methods_disabled(self):
        existing_assessment = Assessment.objects.first()
        self.api_client.force_login(self.admin_user)

        # POST
        url = f"{self.api_base_url}assessments/"
        data = {}
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PUT, PATCH, DELETE
        url = f"{self.api_base_url}assessments/{existing_assessment.id}/"
        response = self.api_client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.api_client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # TEST ANSWER ENDPOINTS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_student_can_submit_answer(self):
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        assessment_block = course_unit.contents.filter(type=BlockType.ASSESSMENT.name).first()
        assessment = assessment_block.assessment
        url = f"{self.api_base_url}answers/"
        data = {
            "assessment": assessment.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "answer": "My answer to the long form question."
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_submit_answer_if_course_is_finished(self):
        self.course.end_date = now() - timedelta(days=1)
        self.course.save()
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        assessment_block = course_unit.contents.filter(type=BlockType.ASSESSMENT.name).first()
        assessment = assessment_block.assessment
        url = f"{self.api_base_url}answers/"
        data = {
            "assessment": assessment.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "answer": "My answer to the long form question."
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_destroy_own_answer(self):
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

        # Now make sure student can't delete it with a 'delete' request
        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_create_answer_when_already_exists(self):
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

        # Now try to POST answer (which the serializer takes to mean 'create a new one')
        # with same student,course and assessment.
        url = f"{self.api_base_url}answers/"
        data = {
            "assessment": assessment.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "answer": f"A new answer for assessment {assessment.id} that I took the time to write, "
                          f"so shouldn't be lost even thought somehow this is getting sent as a POST not PUT."
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['non_field_errors'][0]),
                         "The fields student, assessment, course must make a unique set.")
