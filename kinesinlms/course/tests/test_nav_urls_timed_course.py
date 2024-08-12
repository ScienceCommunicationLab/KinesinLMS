import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now

from kinesinlms.course.models import Enrollment, CourseNode
from kinesinlms.course.tests.factories import TimedCourseFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestNavURLs(TestCase):
    """
    When a user requests a unit, (or a partial URL with just the module slug or a module slug and section slug),
    we load the MPTT-based nav as a dictionary and then cache that dictionary for speed.

    These tests make sure that the correct unit is provided, as well as the previous and next units.

    TODO: Have to refactor this test to make sure "content not available" text is shown
    TODO: in appropriate conditions.

    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        course = TimedCourseFactory()
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

    def test_prev_next_links_when_all_of_timed_course_is_released(self):
        # Change the default setting for the second node from
        # released in the future to released yesterday so that
        # the whole course is released
        node = CourseNode.objects.get(slug='module_3')
        node.release_datetime = now() - timedelta(days=1)
        node.save()

        # build up the urls we expect for prev and next on
        # each page we expect in this course.
        page_urls = []
        module_id = 1
        section_id = 1
        unit_id = 1
        for module_count in range(1, 4):  # 3 modules
            module_slug = f"module_{module_id}"
            module_id += 1
            for section_count in range(1, 3):  # 2 sections per module
                section_slug = f"section_{section_id}"
                section_id += 1
                for unit_count in range(1, 3):  # 2 units per section
                    unit_slug = f"course_unit_{unit_id}"
                    unit_id += 1
                    url = f"{module_slug}/{section_slug}/{unit_slug}/"
                    page_urls.append(url)
        expected_links = []
        for index, url in enumerate(page_urls):
            expected_link = {
                "back_url": None,
                "page_url": url,
                "next_url": None
            }
            if index > 0:
                expected_link['back_url'] = f"/courses/TEST/R1/content/{page_urls[index - 1]}"
            if index < 11:
                expected_link['next_url'] = f"/courses/TEST/R1/content/{page_urls[index + 1]}"
            expected_links.append(expected_link)

        # now test that those are the links we get when we view each page...
        for links in expected_links:
            back_url = links['back_url']
            page_url = links['page_url']
            next_url = links['next_url']

            unit_url = f"{self.course_base_url}{page_url}"
            get_response = self.client.get(unit_url)
            self.assertEqual(get_response.status_code, 200)
            prev_unit_node_url = get_response.context['prev_unit_node_url']
            expected_prev_url = back_url
            self.assertEqual(prev_unit_node_url, expected_prev_url)
            next_unit_node_url = get_response.context['next_unit_node_url']
            expected_next_url = next_url
            self.assertEqual(next_unit_node_url, expected_next_url)

    def test_prev_next_links_when_module_2_not_yet_released(self):

        # make sure module 2 is released in future
        node = CourseNode.objects.get(slug='module_2')
        node.release_datetime = now() + timedelta(days=1)
        node.save()

        # make sure module 3 is released already
        node = CourseNode.objects.get(slug='module_3')
        node.release_datetime = now() - timedelta(days=1)
        node.save()

        # Last unit in module 1 should point to first unit in module 3
        # skiping the unreleased module 2
        unit_url = f"{self.course_base_url}module_1/section_2/course_unit_4/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)

        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = f"/courses/TEST/R1/content/module_1/section_2/course_unit_3/"
        self.assertEqual(prev_unit_node_url, expected_prev_url)

        next_unit_node_url = get_response.context['next_unit_node_url']
        expected_next_url = f"/courses/TEST/R1/content/module_3/section_5/course_unit_9/"
        self.assertEqual(next_unit_node_url, expected_next_url)

    def test_prev_next_links_when_module_3_not_yet_released(self):

        # make sure module 3 is released in future
        node = CourseNode.objects.get(slug='module_3')
        node.release_datetime = now() + timedelta(days=1)
        node.save()

        unit_url = f"{self.course_base_url}module_2/section_4/course_unit_8/"
        get_response = self.client.get(unit_url)
        self.assertEqual(get_response.status_code, 200)
        prev_unit_node_url = get_response.context['prev_unit_node_url']
        expected_prev_url = f"/courses/TEST/R1/content/module_2/section_4/course_unit_7/"
        self.assertEqual(prev_unit_node_url, expected_prev_url)
        next_unit_node_url = get_response.context['next_unit_node_url']
        # Expecting no 'next' url since next module is not yet released
        # and there are no released modules after that one...
        expected_next_url = None
        self.assertEqual(next_unit_node_url, expected_next_url)

    def test_unit_view_when_url_only_has_module(self):
        module_only_url = f"{self.course_base_url}module_1/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/R1/content/module_1/section_1/course_unit_1/"
        self.assertRedirects(get_response, expected_redirect_url)

    def test_unit_view_when_url_has_module_and_section_but_no_unit(self):

        # make sure module 3 is released in future
        node = CourseNode.objects.get(slug='module_3')
        node.release_datetime = now() + timedelta(days=1)
        node.save()

        module_only_url = f"{self.course_base_url}module_1/section_1/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/R1/content/module_1/section_1/course_unit_1/"
        self.assertRedirects(get_response, expected_redirect_url)

        module_only_url = f"{self.course_base_url}module_2/section_3/"
        get_response = self.client.get(module_only_url)
        expected_redirect_url = f"/courses/TEST/R1/content/module_2/section_3/course_unit_5/"
        self.assertRedirects(get_response, expected_redirect_url)
