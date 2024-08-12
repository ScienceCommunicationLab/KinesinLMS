from enum import Enum


class CourseExportFormatID(Enum):
    KINESIN_LMS_FORMAT = "kinesinlms:course_export"
    SCL_FORMAT = "ibiology_courses:course_export"


VALID_COURSE_EXPORT_FORMAT_IDS = [
    CourseExportFormatID.KINESIN_LMS_FORMAT.value,
    CourseExportFormatID.SCL_FORMAT.value
]


class CourseExportFormat(Enum):
    KINESIN_LMS_ZIP = "Kinesin LMS JSON Format"


class CommonCartridgeExportFormat(Enum):
    CC_FULL = "Full Common Cartridge Format"
    CC_SLIM = "Slim Common Cartridge Format"
    # Others?


class ImportCopyType(Enum):
    """
    Different ways an object can
    be copied from existing database
    when doing an import.
    """

    SHALLOW = "shallow"
