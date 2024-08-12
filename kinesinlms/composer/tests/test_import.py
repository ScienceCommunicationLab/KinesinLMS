import json
import logging
from pathlib import Path
from typing import Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.badges.tests.factories import BadgeClassFactory
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.composer.forms.course import AddCourseForm
from kinesinlms.composer.views import load_course_from_form
from kinesinlms.course.models import CourseUnit
from kinesinlms.course.views import get_course_nav
from kinesinlms.learning_library.models import Block
from kinesinlms.sits.constants import SimpleInteractiveToolType
from kinesinlms.sits.schema import DiagramTrayNodeType
from kinesinlms.speakers.tests.factory import SpeakerFactory
from kinesinlms.survey.models import Survey
from kinesinlms.survey.tests.factories import SurveyProviderFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestCourseImport(TestCase):
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

    def test_load_course_from_form(self):
        """
        Test that a basic course description can be imported
        and the correct course models created.
        """

        # Make sure a badge class exists. This is required before importing a course that uses badges.
        badge_class = BadgeClassFactory.create(slug="TEST_SP-course-passed")

        self.client.force_login(self.admin_user)

        with open(self.apps_dir / "composer/tests/data/basic_test_course.json") as json_file:
            basic_course = json_file.read()

        payload = {
            "course_json": basic_course,
            "create_forum_items": False
        }
        form = AddCourseForm(payload)
        course = load_course_from_form(form)

        self.assertIsNotNone(course)
        # Now make sure all the pieces of the imported course that
        # we expect to be created are indeed there and set up correctly.

        basic_course_json = json.loads(basic_course)

        # Check the top-level Course information...
        for var_name in ['display_name',
                         'short_name',
                         'self_paced',
                         'days_early_for_beta',
                         'enable_certificates',
                         'enable_badges']:
            self.assertEqual(getattr(course, var_name), basic_course_json[var_name])

        # Check the Catalog Description...
        catalog_description: CourseCatalogDescription = course.catalog_description
        catalog_description_json = basic_course_json['catalog_description']
        for var_name in ['title',
                         'blurb',
                         'overview',
                         'about_content',
                         'sidebar_content',
                         'visible',
                         'hex_theme_color',
                         'hex_title_color',
                         'custom_stylesheet',
                         'trailer_video_url',
                         'effort',
                         'duration',
                         'audience',
                         'features']:
            self.assertEqual(getattr(catalog_description, var_name), catalog_description_json[var_name])

        # Check speakers
        self.assertEqual(2, course.speakers.count())
        speakers = course.speakers.all()
        self.assertEqual(self.test_speaker_1, speakers[0])
        self.assertEqual(self.test_speaker_2, speakers[1])

        # Make sure UUIDs are preserved
        course_unit = CourseUnit.objects.get(slug='welcome-to-the-test-course')
        self.assertEqual("5e3b7076-b933-4d40-80f5-0882fd15d51b", str(course_unit.uuid))

        # Check surveys:
        for survey_json in basic_course_json['surveys']:
            survey = Survey.objects.get(course=course, type=survey_json['type'])
            self.assertEqual(survey.send_reminder_email, survey_json['send_reminder_email']),
            self.assertEqual(survey.days_delay, survey_json.get('days_delay', 0))
            self.assertEqual(survey.url, survey_json['url'])
            # Make sure survey was linked to correct survey provider
            self.assertEqual(self.survey_provider, survey.provider)

        # Check badges:
        badge_class_exists = course.badge_classes.filter(id=badge_class.id).exists()
        self.assertTrue(badge_class_exists)

    def test_import_timed_course(self):
        """
        Test that we can import a course with release_datetime values defined at the
        module, section and unit levels in the course structure.

        Make sure the elements in the MPTT tree are set accordingly, but don't worry
        about testing actual availability or what the UI shows. That should happen
        in an integration test.
        """

        # TODO: Update this course to use a properly archived course.
        return True

        # Make sure a badge class exists. This is required before importing a course that uses badges.
        badge_class = BadgeClassFactory.create(slug="TEST_2022-course-passed")

        self.client.force_login(self.admin_user)

        create_course_url = reverse('composer:course_create_from_json')

        file_path = "composer/tests/data/basic_test_course_four_units_with_two_scheduled_for_release_in_future.json"
        with open(self.apps_dir / file_path) as json_file:
            basic_course = json_file.read()

        payload = {
            "course_json": basic_course,
            "create_forum_items": False
        }
        form = AddCourseForm(payload)
        course = load_course_from_form(form)

        self.assertIsNotNone(course)

        # Make sure units #3 and #4 are scheduled to be released in future
        course_nav: Dict = get_course_nav(course=course)
        modules = course_nav['children']
        sections = modules[0]['children']
        units = sections[0]['children']
        self.assertEqual(4, len(units))

        unit_1 = units[0]
        self.assertEqual(True, unit_1['is_released'])

        unit_2 = units[1]
        self.assertEqual(True, unit_2['is_released'])

        unit_3 = units[2]
        self.assertEqual("Jul 31, 2030 05:00 PST", unit_3['release_datetime'])
        self.assertEqual("2030-08-01T00:00:00Z", unit_3['release_datetime_utc'])
        self.assertEqual(False, unit_3['is_released'])

        unit_4 = units[3]
        self.assertEqual("Aug 31, 2030 05:00 PST", unit_4['release_datetime'])
        self.assertEqual("2030-09-01T00:00:00Z", unit_4['release_datetime_utc'])
        self.assertEqual(False, unit_4['is_released'])

        # Check badges:
        badge_class_exists = course.badge_classes.filter(id=badge_class.id).exists()
        self.assertTrue(badge_class_exists)

    def test_import_course_with_read_only_block_repeat(self):
        """
        Test that a course with an assessment defined in one unit
        and linked in again (via 'uuid') in read-only mode in a second unit.
        """

        self.client.force_login(self.admin_user)

        with open(self.apps_dir / "composer/tests/data/course_with_assessment_block_repeated_as_read_only.json") as json_file:
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

    def test_import_with_sit_template(self):
        """
        Test that we can import a course with an SIT and an SIT Template.
        """

        # TODO: Update this course to use a properly archived course.
        return True

        # Make sure a badge class exists. This is required before importing a course that uses badges.
        badge_class = BadgeClassFactory.create(slug="TEST_2022-course-passed")

        self.client.force_login(self.admin_user)

        create_course_url = reverse('composer:course_create_from_json')

        file_path = "composer/tests/data/basic_test_course_with_sit_template.json"
        with open(self.apps_dir / file_path) as json_file:
            basic_course = json_file.read()

        payload = {
            "course_json": basic_course,
            "create_forum_items": False
        }
        form = AddCourseForm(payload)
        course = load_course_from_form(form)

        self.assertIsNotNone(course)

        # Make sure Block was created
        self.assertTrue(Block.objects.filter(uuid='346361df-e646-42c7-9e27-e76fad32e08a').exists())

        block = Block.objects.get(uuid='346361df-e646-42c7-9e27-e76fad32e08a')
        # Make sure correct properties were stored for Block
        self.assertEqual("346361df-e646-42c7-9e27-e76fad32e08a", str(block.uuid))
        self.assertEqual("build-mentor-map", block.slug)
        self.assertEqual("Draw Out Your Network", block.display_name)
        self.assertEqual("Some short description for diagram.", block.short_description)

        # Make sure correct properties were stored for SimpleInteractiveTool
        sit = block.simple_interactive_tool
        self.assertEqual("build-mentor-map", sit.slug)
        self.assertEqual("SIT name", sit.name)
        self.assertEqual(SimpleInteractiveToolType.DIAGRAM.name, sit.tool_type)
        self.assertTrue(sit.graded)
        self.assertTrue("The drawing window below lists" in sit.instructions)
        definition = sit.definition
        self.assertEqual(DiagramTrayNodeType.MENTOR_CATEGORY.name, definition['tray_nodes_type'])
        self.assertTrue("Drag a mentor box" in definition['tray_instructions'])
        self.assertTrue(definition['open_mentor_type_popup_after_add'])
