from enum import Enum


class KinesinLMSCourseExportFormatID(Enum):
    KINESIN_LMS_FORMAT = "kinesinlms:course_export"
    IBIO_COURSES_FORMAT = "ibiology_courses:course_export"


VALID_COURSE_EXPORT_FORMAT_IDS = [
    KinesinLMSCourseExportFormatID.KINESIN_LMS_FORMAT.value,
    KinesinLMSCourseExportFormatID.IBIO_COURSES_FORMAT.value,
]

class ImportCopyType(Enum):
    """
    Different ways an object can
    be copied from existing database
    when doing an import.
    """

    SHALLOW = "shallow"
