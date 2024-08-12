import logging
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.custom_app.models import CustomAppTypes
from kinesinlms.custom_app.tests.factories import CustomAppFactory
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestCustomApps(TestCase):
    enrolled_user = None
    course = None

    @classmethod
    def setUpTestData(cls):
        super(TestCustomApps, cls).setUpTestData()
        course = CourseFactory()
        cls.course_base_url = course.course_url
        cls.course = course

        cls.enrolled_user = UserFactory(username="enrolled-user",
                                        email="enrolled-user@example.com")
        Enrollment.objects.create(
            student=cls.enrolled_user,
            course=cls.course,
            active=True
        )

        cls.no_enrollment_user = UserFactory(username="no-enrollment-user",
                                             email="no-enrollment-user@example.com")

        cls.course_speakers_app = CustomAppFactory(display_name="Course speakers",
                                                   type=CustomAppTypes.COURSE_SPEAKERS.name,
                                                   slug="course-speakers",
                                                   course=cls.course,
                                                   description="Meet our teachers!",
                                                   tab_label="Speakers")

        cls.simple_html_content_app = CustomAppFactory(display_name="Some Simple HTML Content",
                                                       type=CustomAppTypes.SIMPLE_HTML_CONTENT.name,
                                                       slug="simple-content",
                                                       course=cls.course,
                                                       description="Some simple HTML content goes here.",
                                                       tab_label="Special")

        # We don't use the Peer Review Journal custom app yet
        # but let's create some tests just to be ready...
        cls.peer_review_journal_app = CustomAppFactory(display_name="Peer Review Journal",
                                                       type=CustomAppTypes.PEER_REVIEW_JOURNAL.name,
                                                       slug="peer-review-journal",
                                                       course=cls.course,
                                                       description="A generic peer review journal.",
                                                       tab_label="Journal")

    def setUp(self):
        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    # Test access...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_course_speakers_page(self):
        self.client.force_login(self.enrolled_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.course_speakers_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_simple_html_content_page(self):
        self.client.force_login(self.enrolled_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.simple_html_content_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_peer_review_journal_page(self):
        self.client.force_login(self.enrolled_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.peer_review_journal_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test access denied...
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_no_access_test_course_speakers_page(self):
        self.client.force_login(self.no_enrollment_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.course_speakers_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_access_simple_html_content_page(self):
        self.client.force_login(self.no_enrollment_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.simple_html_content_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_access_peer_review_journal_content_page(self):
        self.client.force_login(self.no_enrollment_user)
        custom_app_url = reverse('course:custom_app_page',
                                 kwargs={
                                     "course_run": self.course.run,
                                     "course_slug": self.course.slug,
                                     "custom_app_slug": self.peer_review_journal_app.slug
                                 })
        response = self.client.get(custom_app_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
