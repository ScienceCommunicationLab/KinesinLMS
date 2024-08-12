import io
import json
import logging
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.tests.factories import CourseWithRepeatedBlockFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestExportCourseWithRepeatedBlockExport(TestCase):
    """
    Test that ta course that has a repeated block is exported
    correctly: the second and following appearances of a block
    in the export json should only have the 'uuid' field. The entire
    json representation should not be repeated.
    """

    def setUp(self):
        course = CourseWithRepeatedBlockFactory()
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

        course_dict = exported_course_dict['course']
        unit_node_1 = course_dict['course_root_node']['children'][0]['children'][0]['children'][0]
        unit_node_2 = course_dict['course_root_node']['children'][0]['children'][0]['children'][1]

        unit_node_2_unit_block = unit_node_2['unit']['unit_blocks'][0]
        self.assertTrue(unit_node_2_unit_block['read_only'])

        # First appearance of ASSESSMENT type block should have full representation
        unit_node_1_block = unit_node_1['unit']['unit_blocks'][0]['block']
        keys = list(unit_node_1_block.keys())
        self.assertTrue(len(keys) > 5)

        # Second appearance of ASSESSMENT type block should only have a 'slim' representation
        unit_node_2_block = unit_node_2['unit']['unit_blocks'][0]['block']
        keys = list(unit_node_2_block.keys())
        self.assertTrue(len(keys) == 2)
        expected_keys = ["uuid", "type"]
        self.assertEqual(expected_keys, keys, msg="There should only be an 'uuid' "
                                                  "and a 'type' key in the exported Block json")

        # There should only be one  Block of type ASSESSMENT in
        # the DB, so 'objects.get' here is ok...
        block = Block.objects.get(type=BlockType.ASSESSMENT.name)
        uuid_in_block_json = unit_node_2_block['uuid']
        self.assertEqual(str(block.uuid), uuid_in_block_json, msg="The exported Block uuid should be "
                                                                  "the same as what's in the DB.")
