import datetime
import logging
from io import BytesIO
from typing import Dict
from zipfile import ZipFile

import pytz
from rest_framework.renderers import JSONRenderer

from kinesinlms.composer.import_export.config import (
    EXPORT_DOCUMENT_TYPE,
    EXPORTER_VERSION,
)
from kinesinlms.composer.import_export.constants import (
    CourseExportFormat,
)
from kinesinlms.composer.import_export.exporter import BaseExporter
from kinesinlms.course.models import Course, CourseUnit
from kinesinlms.course.serializers import CourseSerializer
from kinesinlms.learning_library.models import Resource

logger = logging.getLogger(__name__)


class KinesinLMSCourseExporter(BaseExporter):
    """
    Exports a course to a standard KinesinLMS format. This format consists mainly
    of a one big json file that contains all the course information, including
    the course structure and all HTML content in the course.

    The json structure matches what our serializers product and expect.

    Resources are exported as files in the final zip file.
    """

    def export_course(self, course: Course, export_format: str) -> BytesIO:
        """
        Exports a course to a JSON format.
        """
        if not course:
            raise ValueError("Course must be specified for export.")
        if not export_format:
            raise ValueError("Export format must be specified.")
        if export_format not in [item.name for item in CourseExportFormat]:
            raise ValueError(f"Export format {export_format} not supported.")

        if export_format == CourseExportFormat.KINESIN_LMS_ZIP.name:
            return self.export_course_to_zip(course)

    def export_course_to_zip(self, course: Course) -> BytesIO:
        """
        Exports a course to a zip file, including a file describing the course
        structure and files for all resources used by the course.

        Args:
            course:             Course to export

        Returns:
            BytesIO containing the zip file

        """
        if course is None:
            raise ValueError("Course must be specified for export.")

        # Write course.json to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        bytes_io = BytesIO()
        zf = ZipFile(bytes_io, "w")
        course_json = self._serialize_course(course)
        zf.writestr("course.json", course_json)

        # Write generic resources to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if bool(course.catalog_description.thumbnail):
            try:
                base_filename = course.catalog_description.thumbnail.name.split("/")[-1]
                export_file_path = f"catalog_resources/thumbnail/{base_filename}"
                with course.catalog_description.thumbnail.open("rb") as source_file:
                    zf.writestr(export_file_path, source_file.read())
                logger.info(f" - exported catalog thumbnail to {export_file_path}")
            except Exception as e:
                logger.error(f"Error writing catalog thumbnail to zip file: {e}")
                raise e

        if bool(course.catalog_description.syllabus):
            try:
                base_filename = course.catalog_description.syllabus.name.split("/")[-1]
                export_file_path = f"catalog_resources/syllabus/{base_filename}"
                with course.catalog_description.syllabus.open("rb") as source_file:
                    zf.writestr(export_file_path, source_file.read())
                logger.info(f"  - exported catalog syllabus to {export_file_path}")
            except Exception as e:
                logger.error(f"Error writing catalog syllabus to zip file: {e}")
                raise e

        # Write block resources to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Gather all Resources for this course via BlockResource
        resources: Dict[str, Resource] = {}
        course_units = CourseUnit.objects.filter(course=course).prefetch_related("contents")
        for course_unit in course_units:
            for block in course_unit.contents.all():
                for resource in block.resources.all():
                    if resource.uuid not in resources:
                        resources[resource.uuid] = resource
        # Write each Resource to the zip file.
        for uuid, resource in resources.items():
            try:
                base_filename = resource.resource_file.name.split("/")[-1]
                export_file_path = f"block_resources/{resource.type.upper()}/{resource.uuid}/{base_filename}"
                with resource.resource_file.open("rb") as source_file:
                    zf.writestr(export_file_path, source_file.read())
            except Exception as e:
                logger.error(f"Error writing resource {resource.uuid} to zip file: {e}")
                raise e

        # Write course resources to zip file
        if hasattr(course, "course_resources"):
            for course_resource in course.course_resources.all():
                try:
                    base_filename = course_resource.resource_file.name.split("/")[-1]
                    export_file_path = f"course_resources/{course_resource.uuid}/{base_filename}"
                    with course_resource.resource_file.open("rb") as source_file:
                        zf.writestr(export_file_path, source_file.read())
                except Exception as e:
                    logger.error(f"Error writing course resource {course_resource.uuid} to zip file: {e}")
                    raise e

        # Finish writing the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        zf.close()

        return bytes_io


    def get_export_filename(self, course: Course) -> str:
        export_filename = "{}_{}_export.klms".format(course.slug, course.run)
        return export_filename

    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _serialize_course(self, course: Course) -> str:
        """
        Serializes top-level course information, including
        course 'description' information for the catalog.

        Args:
            course:     Course to serializer

        Returns:
            Serialized course in json string.
        """

        if course is None:
            raise ValueError("Course must be specified for export.")

        course_data = CourseSerializer(course).data

        course_serialized = {
            "document_type": EXPORT_DOCUMENT_TYPE,
            "metadata": {
                "exporter_version": EXPORTER_VERSION,
                "export_date": datetime.datetime.now(tz=pytz.utc).isoformat(),
            },
            "course": course_data,
        }

        course_json = JSONRenderer().render(course_serialized, renderer_context={"indent": 4})
        return course_json

