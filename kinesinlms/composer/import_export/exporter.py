import logging
from abc import ABC, abstractmethod
from io import BytesIO

from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    @abstractmethod
    def export_course(self, course: Course, export_format: str) -> BytesIO:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_export_filename(self, course: Course) -> str:
        raise NotImplementedError("Subclasses must implement this method.")
