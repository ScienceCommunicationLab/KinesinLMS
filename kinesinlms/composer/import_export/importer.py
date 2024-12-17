import logging
from dataclasses import asdict, dataclass
from enum import Enum
from time import sleep
from typing import Dict, Optional

from django.core.cache import cache

from kinesinlms.composer.import_export.model import CourseImportOptions
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)


class ImportStatusState(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


@dataclass
class ImportStatus:
    percent_complete: int = 0
    progress_message: str = ""
    # course_token only set when status is COMPLETE
    course_token: str = None


class CourseImporterBase:
    """
    Base class for class that imports courses from various sources.

    """

    def __init__(self, cache_key: str = None):
        # Cache key for course import status
        self.cache_key = cache_key

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    def update_cache(self, status: ImportStatus):
        sleep(10)
        if self.cache_key:
            status_dict = asdict(status)
            logger.debug(f"Updating cache {self.cache_key} with status: {status_dict}")
            cache.set(
                self.cache_key,
                status_dict,
                timeout=60 * 60 * 24,
            )
