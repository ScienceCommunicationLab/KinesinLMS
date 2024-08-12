import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestNavURLs(TestCase):
    """
    When a user requests a unit, (or a partial URL with just the module slug or a module slug and section slug),
    we load the MPTT-based nav as a dictionary and then cache that dictionary for speed.

    These tests make sure that the correct unit is provided, as well as the previous and next units.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        course = CourseFactory()
        cls.course = course

        enrolled_user = UserFactory(username="enrolled-user")
        cls.enrolled_user = enrolled_user

        # We have to enroll student to get happy path to work:
        # bookmark API should check to make sure student is
        # enrolled before making bookmark.
        enrollment, created = Enrollment.objects.get_or_create(student=enrolled_user,
                                                               course=course,
                                                               active=True)
        cls.enrollment = enrollment

    def setUp(self):
        self.course_base_url = f"https://localhost:8000{self.course.course_url}"
        self.client.force_login(self.enrolled_user)

    def test_unit_views_when_url_is_complete(self):
        unit_urls = [
            {"url": "basic_module/basic_section_1/course_unit_1/", "expected_code": 200},
            {"url": "basic_module/basic_section_1/course_unit_2/", "expected_code": 200},
            {"url": "basic_module/basic_section_2/course_unit_3/", "expected_code": 200},
            {"url": "basic_module/basic_section_2/course_unit_4/", "expected_code": 200},
            {"url": "advanced_module/advanced_section_3/course_unit_5/", "expected_code": 200},
            {"url": "advanced_module/advanced_section_3/course_unit_6/", "expected_code": 200}
        ]

        for unit_url in unit_urls:
            partial_url = unit_url['url']
            expected_code = unit_url['expected_code']
            full_url = f"{self.course_base_url}{partial_url}"
            get_response = self.client.get(full_url)
            self.assertEqual(expected_code, get_response.status_code)
            if expected_code == 200:
                url_parts = partial_url.split("/")
                unit_slug = url_parts[-1]
                # check page content to make sure correct unit was loaded
                self.assertContains(get_response, f"Some video header for {unit_slug}")

    def test_prev_next_links(self):
        # COURSE UNIT 1
        unit_url = f"{self.course_base_url}basic_module/basic_section_1/course_unit_1/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)
        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = None
        self.assertEqual(expected_prev_url, prev_unit_node_url)
        next_unit_node_url = get_response.context['next_unit_node_url']
        expected_next_url = f"/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_2/"
        self.assertEqual(expected_next_url, next_unit_node_url)

        # COURSE UNIT 2
        unit_url = f"{self.course_base_url}basic_module/basic_section_1/course_unit_2/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)
        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = f"/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_1/"
        self.assertEqual(expected_prev_url, prev_unit_node_url)
        next_unit_node_url = get_response.context['next_unit_node_url']
        expected_next_url = f"/courses/TEST/SP/content/basic_module/basic_section_2/course_unit_3/"
        self.assertEqual(expected_next_url, next_unit_node_url)

        # COURSE UNIT 3
        unit_url = f"{self.course_base_url}basic_module/basic_section_2/course_unit_3/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)
        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = f"/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_2/"
        self.assertEqual(expected_prev_url, prev_unit_node_url)
        next_unit_node_url = get_response.context['next_unit_node_url']
        expected_next_url = f"/courses/TEST/SP/content/basic_module/basic_section_2/course_unit_4/"
        self.assertEqual(expected_next_url, next_unit_node_url)

        # COURSE UNIT 4
        unit_url = f"{self.course_base_url}basic_module/basic_section_2/course_unit_4/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)
        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = f"/courses/TEST/SP/content/basic_module/basic_section_2/course_unit_3/"
        self.assertEqual(expected_prev_url, prev_unit_node_url)
        next_unit_node_url = get_response.context['next_unit_node_url']
        expected_next_url = f"/courses/TEST/SP/content/advanced_module/advanced_section_3/course_unit_5/"
        self.assertEqual(expected_next_url, next_unit_node_url)

        # COURSE UNIT 5
        unit_url = f"{self.course_base_url}advanced_module/advanced_section_3/course_unit_5/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)

        # COURSE UNIT 6
        unit_url = f"{self.course_base_url}advanced_module/advanced_section_3/course_unit_6/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)

    def test_unit_view_when_url_only_has_module(self):
        module_only_url = f"{self.course_base_url}basic_module/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_1/"
        self.assertRedirects(get_response, expected_redirect_url)

        module_only_url = f"{self.course_base_url}advanced_module/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/SP/content/advanced_module/advanced_section_3/course_unit_5/"
        # Can't use assertRedirects b/c this module is not released yet and redirect will return 404.
        # So just make sure it's pointing in the right place...
        self.assertEqual(expected_redirect_url, get_response.url)

    def test_unit_view_when_url_has_module_and_section_but_no_unit(self):
        module_only_url = f"{self.course_base_url}basic_module/basic_section_1/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/SP/content/basic_module/basic_section_1/course_unit_1/"
        self.assertRedirects(get_response, expected_redirect_url)

        module_only_url = f"{self.course_base_url}basic_module/basic_section_2/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/SP/content/basic_module/basic_section_2/course_unit_3/"
        self.assertRedirects(get_response, expected_redirect_url)

        module_only_url = f"{self.course_base_url}basic_module/advanced_section_3/"
        get_response = self.client.get(module_only_url)
        # This module is set in the future so should be unavailable...
        expected_response_code = 404
        self.assertEqual(expected_response_code, get_response.status_code)
