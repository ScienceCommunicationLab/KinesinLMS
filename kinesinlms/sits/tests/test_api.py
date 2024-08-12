import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from kinesinlms.course.models import Enrollment, CourseUnit
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.sits.models import SimpleInteractiveTool, SimpleInteractiveToolSubmission
from kinesinlms.sits.tests.factories import SimpleInteractiveToolSubmissionFactory
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent

logger = logging.getLogger(__name__)


class TestDiagramsAPI(TestCase):
    """
    Test all API endpoints related to this module.
    """

    enrolled_user = None
    other_enrolled_user = None
    course = None

    @classmethod
    def setUpTestData(cls) -> None:
        User = get_user_model()
        cls.enrolled_user = User.objects.create(username="enrolled-user")
        cls.other_enrolled_user = User.objects.create(username="other-enrolled-user")
        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

        course = CourseFactory()
        cls.course = course

        Enrollment.objects.get_or_create(student=cls.enrolled_user,
                                         course=cls.course,
                                         active=True)

        Enrollment.objects.get_or_create(student=cls.other_enrolled_user,
                                         course=cls.course,
                                         active=True)
        cls.api_client = APIClient()
        cls.api_base_url = f"https://localhost:8000/api/"

    # TEST ASSESSMENT ENDPOINTS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # For Admins...

    def test_admin_can_list_simple_interactive_tools(self):
        self.api_client.force_login(self.admin_user)
        url = f"{self.api_base_url}simple_interactive_tools/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), SimpleInteractiveTool.objects.count())

    def test_admin_can_view_simple_interactive_tool_detail(self):
        existing_simple_interactive_tool = SimpleInteractiveTool.objects.first()
        self.api_client.force_login(self.admin_user)
        url = f"{self.api_base_url}simple_interactive_tools/{existing_simple_interactive_tool.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # For students...

    def test_student_cannot_list_simple_interactive_tools(self):
        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}simple_interactive_tools/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_view_simple_interactive_tool_detail(self):
        existing_simple_interactive_tool = SimpleInteractiveTool.objects.first()
        self.api_client.force_login(self.enrolled_user)
        url = f"{self.api_base_url}simple_interactive_tools/{existing_simple_interactive_tool.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_rest_methods_disabled_for_students(self):
        existing_simple_interactive_tool = SimpleInteractiveTool.objects.first()
        self.api_client.force_login(self.enrolled_user)

        # POST
        url = f"{self.api_base_url}simple_interactive_tools/"
        data = {}
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PUT, PATCH, DELETE
        url = f"{self.api_base_url}assessments/{existing_simple_interactive_tool.id}/"
        response = self.api_client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.api_client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # TEST ANSWER ENDPOINTS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_student_can_submit_simple_interactive_tool(self):
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        simple_interactive_tool_block = course_unit.contents.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name).first()
        simple_interactive_tool = simple_interactive_tool_block.simple_interactive_tool
        url = f"{self.api_base_url}simple_interactive_tool_submissions/"
        data = {
            "simple_interactive_tool": simple_interactive_tool.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "diagram": {
                    "some": "diagram structure"
                }
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sit_submission_creates_event(self):
        self.api_client.force_login(self.enrolled_user)

        # Make sure there are no events before starting
        self.assertTrue(TrackingEvent.objects.count() == 0)

        course_unit = CourseUnit.objects.first()
        simple_interactive_tool_block = course_unit.contents.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name).first()
        simple_interactive_tool = simple_interactive_tool_block.simple_interactive_tool
        url = f"{self.api_base_url}simple_interactive_tool_submissions/"
        data = {
            "simple_interactive_tool": simple_interactive_tool.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "diagram": {
                    "some": "diagram structure"
                }
            }
        }
        response = self.api_client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        event_count = TrackingEvent.objects.filter(
            event_type=TrackingEventType.COURSE_SIMPLE_INTERACTIVE_TOOL_SUBMITTED.value,
            course_slug=self.course.slug,
            course_run=self.course.run,
            user=self.enrolled_user).count()
        self.assertEqual(event_count, 1)

    def test_student_can_update_existing_simple_interactive_tool_answer(self):
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        simple_interactive_tool_block = course_unit.contents.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name).first()
        simple_interactive_tool = simple_interactive_tool_block.simple_interactive_tool

        # Create a pre-existing answer...
        submission = SimpleInteractiveToolSubmissionFactory(course=self.course,
                                                            simple_interactive_tool=simple_interactive_tool,
                                                            student=self.enrolled_user)

        # Now try to update it...
        url = f"{self.api_base_url}simple_interactive_tool_submissions/{submission.id}/"
        data = {
            "simple_interactive_tool": simple_interactive_tool.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "diagram": {
                    "some": "my diagram structure"
                }
            }
        }
        response = self.api_client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission = SimpleInteractiveToolSubmission.objects.get(id=submission.id)
        self.assertEqual("my diagram structure", submission.json_content.get('diagram').get('some'))

    def test_student_cannot_destroy_own_simple_interative_tool_submission(self):
        self.api_client.force_login(self.enrolled_user)
        course_unit = CourseUnit.objects.first()
        simple_interactive_tool_block = course_unit.contents.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name).first()
        simple_interactive_tool = simple_interactive_tool_block.simple_interactive_tool

        # add an existing answer
        submission = SimpleInteractiveToolSubmissionFactory(course=self.course,
                                                            simple_interactive_tool=simple_interactive_tool,
                                                            student=self.enrolled_user)

        # Make sure the answer is there
        url = f"{self.api_base_url}simple_interactive_tool_submissions/{submission.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now make sure student can't delete it with a 'delete' request
        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_student_cannot_update_other_students_answer(self):
        course_unit = CourseUnit.objects.first()
        simple_interactive_tool_block = course_unit.contents.filter(type=BlockType.SIMPLE_INTERACTIVE_TOOL.name).first()
        simple_interactive_tool = simple_interactive_tool_block.simple_interactive_tool

        # Add a previous answer by other student
        submission_by_other_student = SimpleInteractiveToolSubmissionFactory(
            course=self.course,
            simple_interactive_tool=simple_interactive_tool,
            student=self.other_enrolled_user)

        # Make sure the answer is there ...
        self.api_client.force_login(self.other_enrolled_user)
        url = f"{self.api_base_url}simple_interactive_tool_submissions/{submission_by_other_student.id}/"
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # And other student can update it...
        data = {
            "simple_interactive_tool": simple_interactive_tool.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "diagram": {
                    "some": "I'm other student and I'm changing my own diagram"
                }
            }
        }
        response = self.api_client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now make sure student cannot update it or delete it.
        self.api_client.force_login(self.enrolled_user)
        data = {
            "simple_interactive_tool": simple_interactive_tool.id,
            "course": self.course.id,
            "course_unit": course_unit.id,
            "json_content": {
                "diagram": {
                    "some": "I'm mischievous and I'm trying to change other student's diagram"
                }
            }
        }
        response = self.api_client.put(url, data=data, format='json')
        # This answer should not be a part of the sit answer queryset,
        # as it is filtered by current user's ID. So we expect a 404.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
