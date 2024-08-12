import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory

import logging
logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestBookmarks(TestCase):

    def setUp(self):

        self.course = CourseFactory()
        self.course_base_url = self.course.course_url

        User = get_user_model()
        self.enrolled_user = User.objects.create(username="enrolled-user")
        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

        # We have to enroll student to get happy path to work:
        # bookmark API should check to make sure student is
        # enrolled before making bookmark.
        enrollment, created = Enrollment.objects.get_or_create(student=self.enrolled_user,
                                                               course=self.course,
                                                               active=True)
        self.enrollment = enrollment

        # Get a unit to use in tests.
        first_module_node = self.course.course_root_node.get_descendants().first()
        first_section_node = first_module_node.get_descendants().first()
        self.first_unit_node = first_section_node.get_descendants().first()

        self.valid_bookmark_event = {
            "student": self.enrolled_user.id,
            "course": self.course.id,
            "unit_node": self.first_unit_node.id,
        }

    def test_bookmark(self):
        self.client.force_login(self.enrolled_user)
        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(self.valid_bookmark_event),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 201)
