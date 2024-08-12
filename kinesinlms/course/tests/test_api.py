import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from kinesinlms.course.models import Enrollment, Bookmark, CourseNode
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestAPI(TestCase):
    """
    Test all API endpoints related to this module.
    """

    def setUp(self):
        course = CourseFactory()
        self.course = course

        User = get_user_model()
        self.enrolled_user = User.objects.create(username="enrolled-user")
        self.enrolled_user_2 = User.objects.create(username="enrolled-user-2")
        self.admin_user = User.objects.create(username="daniel",
                                              is_staff=True,
                                              is_superuser=True)

        # We have to enroll student to get happy path to work:
        # bookmark API should check to make sure student is
        # enrolled before making bookmark.
        enrollment, created = Enrollment.objects.get_or_create(student=self.enrolled_user,
                                                               course=self.course,
                                                               active=True)
        self.enrollment = enrollment
        enrollment_2, created = Enrollment.objects.get_or_create(student=self.enrolled_user_2,
                                                                 course=self.course,
                                                                 active=True)
        self.enrollment_2 = enrollment_2

        self.api_base_url = f"https://localhost:8000/api/"
        unit_nodes = CourseNode.objects.all()
        self.unit_node_1 = unit_nodes[0]
        self.unit_node_2 = unit_nodes[1]
        self.bookmark_1 = Bookmark.objects.get_or_create(student=self.enrolled_user,
                                                         unit_node=self.unit_node_1,
                                                         course=course)
        self.bookmark_2 = Bookmark.objects.get_or_create(student=self.enrolled_user,
                                                         unit_node=self.unit_node_2,
                                                         course=course)

        # Make a bookmark by another user to make sure student can't view.
        self.other_user_bookmark_1 = Bookmark.objects.get_or_create(student=self.enrolled_user_2,
                                                                    unit_node=self.unit_node_1,
                                                                    course=course)

    def test_course_disallowed(self):
        """
        Make sure students can't access protected endpoints.
        """
        self.client.force_login(self.enrolled_user)
        response = self.client.get(f"{self.api_base_url}courses/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(f"{self.api_base_url}courses/{self.course.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.put(f"{self.api_base_url}courses/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.put(f"{self.api_base_url}courses/{self.course.id}/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(f"{self.api_base_url}courses/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f"{self.api_base_url}courses/{self.course.id}/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_list(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"{self.api_base_url}courses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_list = response.data
        first_course = course_list[0]
        self.assertEqual(first_course.get("slug", None), "TEST")

    def test_course_detail(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"{self.api_base_url}courses/{self.course.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_json = response.data
        self.assertEqual(course_json.get("slug", None), "TEST")

    def test_course_nav_disallowed(self):
        self.client.force_login(self.enrolled_user)
        response = self.client.get(f"{self.api_base_url}course_nav/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(f"{self.api_base_url}course_nav/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.put(f"{self.api_base_url}course_nav/{self.course.id}/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(f"{self.api_base_url}course_nav/{self.course.id}/", data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f"{self.api_base_url}course_nav/{self.course.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_nav_detail(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"{self.api_base_url}course_nav/{self.course.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_json = response.data
        self.assertEqual(course_json.get("type", None), "ROOT")

    def test_student_can_view_bookmarks(self):
        """
        Remember that accessing the bookmark API directly gives
        a student a list of all bookmarks, not just one in a certain course.
        But student should not see other user's bookmarks
        :return:
        """
        self.client.force_login(self.enrolled_user)
        response = self.client.get(f"{self.api_base_url}bookmarks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bookmarks = response.data
        self.assertEqual(len(bookmarks), 2)
        bookmark_1 = bookmarks[0]
        self.assertEqual(bookmark_1['student'], self.enrolled_user.id)
        self.assertEqual(bookmark_1['course'], self.course.id)
        self.assertEqual(bookmark_1['unit_node'], self.unit_node_1.id)

    def test_admin_can_view_all_bookmarks(self):
        """
        Admin should see bookmarks for all users
        :return:
        """
        self.client.force_login(self.admin_user)
        response = self.client.get(f"{self.api_base_url}bookmarks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bookmarks = response.data
        self.assertEqual(len(bookmarks), 3)
        bookmark_1 = bookmarks[0]
        self.assertEqual(bookmark_1['student'], self.enrolled_user.id)
        self.assertEqual(bookmark_1['course'], self.course.id)
        self.assertEqual(bookmark_1['unit_node'], self.unit_node_1.id)
        bookmark_1 = bookmarks[2]
        self.assertEqual(bookmark_1['student'], self.enrolled_user_2.id)
        self.assertEqual(bookmark_1['course'], self.course.id)
        self.assertEqual(bookmark_1['unit_node'], self.unit_node_1.id)
