import json
import logging
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.utils.timezone import now

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/tracking/'


class TestTrackingViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        course = CourseFactory()
        course = course
        cls.course = course

        User = get_user_model()
        enrolled_user = User.objects.create(username="enrolled-user")
        cls.enrolled_user = enrolled_user

        Enrollment.objects.get_or_create(student=enrolled_user,
                                         course=course,
                                         active=True)

        # Get a unit to use in tests.
        first_module_node = course.course_root_node.get_descendants().first()
        first_section_node = first_module_node.get_descendants().first()
        first_unit_node = first_section_node.get_descendants().first()
        unit_node = first_unit_node
        unit_block = first_unit_node.unit
        video_block = unit_block.contents.first()
        cls.unit_node = unit_node
        cls.unit_block = unit_block
        cls.video_block = video_block

        cls.valid_tracking_event = {
            "event_type": TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
            "course_run": course.run,
            "course_slug": course.slug,
            "unit_node_slug": unit_node.slug,
            "course_unit_id": video_block.id,
            "course_unit_slug": video_block.slug,
            "block_uuid": video_block.uuid,
            "event_data": {
                "video_id": "abc",
                "video_event_type": "kinesinlms.course.video.play"
            }
        }

    def setUp(self) -> None:
        # mock the calls to external tracking API
        patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        patcher.start()
        self.patcher = patcher

    def test_create_video_tracking_event(self):
        self.client.force_login(self.enrolled_user)
        # Pass in correct structure for video event
        # This would be generated and sent in by, e.g. React-based component.

        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(self.valid_tracking_event, indent=4, cls=DjangoJSONEncoder),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, TrackingEvent.objects.count())

    def test_video_tracking_event_is_saved_event_if_course_has_finished(self):
        """
        If a course has finished, tracking events will still be accepted
        and saved for certain course events, such as video plays.
        """

        self.course.self_paced = False
        self.course.end_date = now() - timedelta(days=1)
        self.course.save()

        self.client.force_login(self.enrolled_user)
        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(self.valid_tracking_event, indent=4, cls=DjangoJSONEncoder),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, TrackingEvent.objects.count())

    def test_must_be_logged_in(self):
        # Don't force login in this test!
        self.client.logout()
        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(self.valid_tracking_event, indent=4, cls=DjangoJSONEncoder),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_need_block_id_for_tracking(self):
        self.client.force_login(self.enrolled_user)
        tracking_event = self.valid_tracking_event
        tracking_event.pop('course_unit_id')
        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(tracking_event, indent=4, cls=DjangoJSONEncoder),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_need_video_id_for_tracking(self):
        self.client.force_login(self.enrolled_user)
        tracking_event = self.valid_tracking_event
        tracking_event['event_data'].pop('video_id')
        response = self.client.post(TRACKING_API_ENDPOINT,
                                    data=json.dumps(tracking_event, indent=4, cls=DjangoJSONEncoder),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
