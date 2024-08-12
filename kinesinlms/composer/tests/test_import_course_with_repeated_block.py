import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from kinesinlms.composer.forms.course import AddCourseForm
from kinesinlms.composer.views import load_course_from_form
from kinesinlms.course.models import CourseUnit
from kinesinlms.speakers.tests.factory import SpeakerFactory
from kinesinlms.survey.tests.factories import SurveyProviderFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestCourseImportWithRepeatedBlockInReadOnly(TestCase):
    """
    Course import takes a json representation of a course
    and builds out a complete course, including navigation,
    surveys, etc.

    This class tests the various aspects of the import
    to make sure all parts of the json are created correctly.

    """

    @classmethod
    def setUpTestData(cls) -> None:
        User = get_user_model()

        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

        cls.apps_dir = Path(settings.APPS_DIR)

        cls.test_speaker_1 = SpeakerFactory(full_name="Test Speaker 1",
                                            slug='test-speaker-1')
        cls.test_speaker_2 = SpeakerFactory(full_name="Test Speaker 2",
                                            slug='test-speaker-2')

        cls.survey_provider = SurveyProviderFactory(slug='qualtrics-kinesinlms')

    def test_import(self):
        """
        Test that a course with an assessment defined in one unit
        and linked in again (via 'uuid') in read-only mode in a second unit.
        """

        self.client.force_login(self.admin_user)

        with open(
                self.apps_dir / "composer/tests/data/course_with_assessment_block_repeated_as_read_only.json") as json_file:
            basic_course = json_file.read()

        payload = {
            "course_json": basic_course,
            "create_forum_items": False
        }
        form = AddCourseForm(payload)
        course = load_course_from_form(form)

        self.assertIsNotNone(course)

        # Get the two UNIT CourseNodes and make sure they include
        # the *same* Assessment block.

        assessment_unit = CourseUnit.objects.get(slug='assessment-unit')
        read_only_unit = CourseUnit.objects.get(slug='read-only-unit')

        assessment_block = assessment_unit.contents.first()
        read_only_assessment_block = read_only_unit.contents.first()

        self.assertEqual(assessment_block.id, read_only_assessment_block.id)
