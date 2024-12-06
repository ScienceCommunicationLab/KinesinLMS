import logging
from typing import Dict, Optional

from django.db import transaction

from kinesinlms.composer.import_export.model import CourseImportOptions
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)


class CourseImporterBase:
    """
    Base class for class that imports courses from various sources.

    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @transaction.atomic
    def import_course_from_json(
        self,
        course_json: Dict,
        course_slug: str = None,
        course_run: str = None,
        display_name: str = None,
        options: CourseImportOptions = None,  # noqa: F841
    ) -> Course:
        """
        Import a course from a JSON representation.

        Args:
            course_json:    JSON representation of the course
            course_slug:    Course slug
            course_run:     Course run
            display_name:   Display name for the course
            options:        CourseImportOptions instance with options for import.

        Returns:
            Course instance
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @transaction.atomic
    def import_course_from_archive(
        self,
        file,
        display_name: str,
        course_slug: str,
        course_run: str,
        options: CourseImportOptions = None,
    ) -> Optional[Course]:
        """
        Load a course and related resources from a course archive (.zip) file.

        Args:
            file:
            display_name:
            course_slug:
            course_run:
            options:            CourseImportOptions instance with options for import.

        Returns:
            Course instance or None
        """

    raise NotImplementedError("Subclasses must implement this method.")
