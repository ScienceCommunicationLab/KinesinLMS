import io
import json
import logging
import zipfile

import deepdiff
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestComposerCourseExport(TestCase):
    """
    Test that we can export a course to KinesinLMS format.
    """

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        User = get_user_model()
        self.admin_user = User.objects.create(username="daniel",
                                              is_staff=True,
                                              is_superuser=True)

    def test_course_export(self):
        self.client.force_login(self.admin_user)
        course = self.course
        export_url = reverse('composer:course_download_export', kwargs={
            'course_slug': course.slug,
            'course_run': course.run
        })
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)

        f = io.BytesIO(response.content)
        zipped_file = zipfile.ZipFile(f, 'r')
        self.assertIn('course.json', zipped_file.namelist())
        course_json = zipped_file.read('course.json')
        zipped_file.close()
        f.close()

        exported_course_dict = json.loads(course_json)
        self.assertIsNotNone(exported_course_dict)

        # We only want to compare the 'course' dictionary
        # not the top-level stuff that includes meta info.
        course_dict = exported_course_dict['course']

        # Don't worry about testimonials
        course_dict['catalog_description'].pop('testimonials', None)

        expected_course_path = settings.APPS_DIR / 'composer' / 'tests' / 'data' / 'expected_course_export_TEST_SP.json'
        with open(str(expected_course_path)) as data_file:
            expected_course_dict = json.load(data_file)['course']

        # pretty print course_dict
        logger.debug(f"course_dict: {json.dumps(course_dict, indent=4)}")

        diff = deepdiff.DeepDiff(expected_course_dict, course_dict)
        type_changes = diff.get('type_changes', [])
        self.assertTrue(len(type_changes) == 0)

        dictionary_item_added = diff.get('dictionary_item_added', [])
        logger.debug(f"dictionary_item_added: {dictionary_item_added}")
        self.assertTrue(len(dictionary_item_added) == 0)

        dictionary_item_removed = diff.get('dictionary_item_removed', [])
        self.assertTrue(len(dictionary_item_removed) == 0)
