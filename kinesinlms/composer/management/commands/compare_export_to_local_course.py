import json
import logging
import zipfile

import deepdiff
from django.core.management.base import BaseCommand

from kinesinlms.composer.import_export.constants import CourseExportFormat
from kinesinlms.composer.import_export.exporter import CourseExporter
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Compare a course export to expected json."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        parser.add_argument('--course', type=str, default='')
        parser.add_argument('--path', type=str, default='')

    def handle(self, *args, **options):
        token = options['course']
        slug, run = token.split("_")

        exported_json_path = options['path']

        try:
            course = Course.objects.get(slug=slug, run=run)
        except Course.DoesNotExist as e:
            self.stdout.write(f"NO ACTION! Can't find course with token {token}")
            raise e

        # Get JSON
        # ......................

        # Local course
        course_exporter = CourseExporter()
        local_course_zip = course_exporter.export_course(course,
                                                         export_format=CourseExportFormat.KINESIN_LMS_ZIP.name)

        try:
            with zipfile.ZipFile(local_course_zip, 'r') as zip_ref:
                with zip_ref.open('course.json', 'r') as course_file:
                    local_course_str = course_file.read().decode('utf-8')
                    local_course_dict = json.loads(local_course_str)
        except (FileNotFoundError, zipfile.BadZipFile) as e:
            print("Error opening or reading course.json from zip file:", e)
            local_course_dict = None

        # Expected course json
        with open(str(exported_json_path)) as data_file:
            expected_course_dict = json.load(data_file)

        # Compare
        # ......................
        logger.info("Comparing expected course json to exported course json...")

        # We only want to compare the 'course' dictionary
        # not the top-level stuff that includes meta info.
        expected_course_dict = expected_course_dict['course']

        diff = deepdiff.DeepDiff(local_course_dict, expected_course_dict)
        type_changes = diff.get('type_changes', [])
        logger.info(f"type changed: {type_changes}")

        dictionary_item_added = diff.get('dictionary_item_added', [])
        logger.info(f"added items: {dictionary_item_added}")

        dictionary_item_removed = diff.get('dictionary_item_removed', [])
        logger.info(f"removed items: {dictionary_item_removed}")
